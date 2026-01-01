from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import PurchaseOrder, PurchaseOrderItem, PurchaseRequisition
from .serializers import PurchaseOrderSerializer, PurchaseRequisitionSerializer


def _is_int_decimal(value: Decimal) -> bool:
    try:
        return value == value.to_integral_value()
    except Exception:
        return False


def _get_permission_instances():
    if getattr(settings, "DEBUG", False):
        return [AllowAny()]
    return [IsAuthenticated()]


def _receive_purchase_order_in_atomic(po: PurchaseOrder, *, actor: str) -> None:
    """Receive stock for a PO. Must be called inside an atomic block."""

    items = po.items.select_related("inventory_item", "product").all()
    if not items:
        raise ValueError("Purchase order has no items.")

    # Import here to reduce import-time coupling.
    from products.models.inventory_model import InventoryItem, StockMovement
    from products.models.product_model import Product

    for it in items:
        qty = it.quantity
        if qty is None or qty <= 0:
            raise ValueError(f"Invalid quantity for item {it.uuid}.")

        # Prefer explicit inventory_item on PO item.
        inventory_item_id = it.inventory_item_id
        if inventory_item_id is None and it.product_id is not None:
            # If product is linked to an inventory item, use it.
            inventory_item_id = (
                Product.objects.filter(pk=it.product_id)
                .values_list("inventory_item__id", flat=True)
                .first()
            )

        if inventory_item_id is not None:
            inv = InventoryItem.objects.select_for_update().get(pk=inventory_item_id)
            previous_stock = inv.current_stock
            inv.current_stock = inv.current_stock + qty
            # Optional metadata from PO line.
            if it.expiry_date is not None:
                inv.expiry_date = it.expiry_date
            if it.warranty_expiry_date is not None:
                inv.warranty_expiry_date = it.warranty_expiry_date
            inv.save()

            StockMovement.objects.create(
                inventory_item=inv,
                movement_type="in",
                quantity=qty,
                previous_stock=previous_stock,
                new_stock=inv.current_stock,
                reason=f"PO Receive {po.po_number}",
                notes=po.notes or "",
                reference_number=po.po_number,
                created_by=actor,
            )

        # Legacy product stock update for POS products (int-only)
        if it.product_id is not None:
            if not isinstance(qty, Decimal):
                qty = Decimal(str(qty))

            if _is_int_decimal(qty):
                qty_int = int(qty)
                Product.objects.filter(pk=it.product_id).update(
                    quantity=F("quantity") + qty_int,
                    in_stock=F("in_stock") + qty_int,
                    totalPurchase=F("totalPurchase") + qty_int,
                    out_of_stock=False,
                    status="in stock",
                )

    po.status = "delivered"
    po.save(update_fields=["status", "updated_at"])

    if po.requisition_id and po.requisition.status == "approved":
        po.requisition.status = "converted"
        po.requisition.save(update_fields=["status", "updated_at"])


class PurchaseRequisitionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Purchase Requisitions
    Supports create, read, update, delete operations
    """

    # Uses project DEFAULT_AUTHENTICATION_CLASSES (Token + JWT)
    permission_classes = [IsAuthenticated]

    serializer_class = PurchaseRequisitionSerializer

    def get_permissions(self):
        return _get_permission_instances()

    def get_queryset(self):
        # In production, filter by company: company_id=self.request.user.company_id
        return PurchaseRequisition.objects.all().order_by("-request_date")

    def perform_create(self, serializer):
        # In production, add: company=self.request.user.company
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        requisition: PurchaseRequisition = self.get_object()
        if requisition.status == "approved":
            return Response(
                {"detail": "Approved requisitions cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        requisition: PurchaseRequisition = self.get_object()
        if requisition.status in {"approved", "rejected", "converted"}:
            return Response(
                {
                    "detail": f"{requisition.status.capitalize()} requisitions cannot be edited."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        requisition: PurchaseRequisition = self.get_object()
        if requisition.status == "approved":
            incoming = request.data if isinstance(request.data, dict) else {}
            # Allow only status transition to 'converted' for approved requisitions
            if not (
                set(incoming.keys()) <= {"status"}
                and incoming.get("status") == "converted"
            ):
                return Response(
                    {
                        "detail": "Approved requisitions cannot be edited (only conversion is allowed)."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if requisition.status in {"rejected", "converted"}:
            return Response(
                {
                    "detail": f"{requisition.status.capitalize()} requisitions cannot be edited."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="purchase")
    def purchase(self, request, *args, **kwargs):
        """Receive stock for an approved requisition.

        - Requires `status=approved`
        - direct_inventory: updates Product stock (int-only) and creates an audit PO
        - raw_material/asset: creates a PO and receives InventoryItem stock atomically
        """

        requisition: PurchaseRequisition = self.get_object()

        if requisition.status != "approved":
            return Response(
                {"detail": "Requisition must be approved before purchasing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = requisition.items.select_related("product", "inventory_item").all()
        if not items:
            return Response(
                {"detail": "Requisition has no items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        actor = (
            request.user.username
            if request.user and request.user.is_authenticated
            else "Anonymous"
        )

        with transaction.atomic():
            if requisition.purchase_type == "direct_inventory":
                missing_products = [
                    str(it.uuid) for it in items if it.product_id is None
                ]
                if missing_products:
                    return Response(
                        {
                            "detail": "All items must select a product for direct_inventory requisitions.",
                            "missing_items": missing_products,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Import here to reduce import-time coupling.
                from products.models.product_model import Product

                for it in items:
                    qty = it.quantity
                    if qty is None or qty <= 0:
                        return Response(
                            {"detail": f"Invalid quantity for item {it.uuid}."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if not isinstance(qty, Decimal):
                        try:
                            qty = Decimal(str(qty))
                        except Exception:
                            return Response(
                                {"detail": f"Invalid quantity for item {it.uuid}."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                    if not _is_int_decimal(qty):
                        return Response(
                            {
                                "detail": f"Quantity for item {it.uuid} must be a whole number for product purchases.",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    qty_int = int(qty)

                    Product.objects.filter(pk=it.product_id).update(
                        quantity=F("quantity") + qty_int,
                        in_stock=F("in_stock") + qty_int,
                        totalPurchase=F("totalPurchase") + qty_int,
                        out_of_stock=False,
                        status="in stock",
                    )

                requisition.status = "converted"
                requisition.save(update_fields=["status", "updated_at"])

                po = PurchaseOrder.objects.create(
                    requisition=requisition,
                    supplier=None,
                    status="delivered",
                    notes=f"Auto-created from {requisition.pr_number}",
                    created_by=actor,
                )
                for it in items:
                    PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        product=it.product,
                        inventory_item=None,
                        name=it.item_name,
                        quantity=it.quantity,
                        unit=it.unit,
                        unit_price=Decimal("0"),
                    )
                po.recalc_total()
            else:
                missing_inventory = [
                    str(it.uuid) for it in items if it.inventory_item_id is None
                ]
                if missing_inventory:
                    return Response(
                        {
                            "detail": "All items must select an inventory item for raw_material/asset requisitions.",
                            "missing_items": missing_inventory,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                po = PurchaseOrder.objects.create(
                    requisition=requisition,
                    supplier=None,
                    status="pending",
                    notes=f"Auto-created from {requisition.pr_number}",
                    created_by=actor,
                )
                for it in items:
                    PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        inventory_item=it.inventory_item,
                        product=None,
                        name=it.item_name,
                        quantity=it.quantity,
                        unit=it.unit,
                        unit_price=Decimal("0"),
                    )
                po.recalc_total()

                try:
                    _receive_purchase_order_in_atomic(po, actor=actor)
                except Exception as exc:
                    return Response(
                        {"detail": str(exc) or "Failed to receive purchase order."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        serializer = self.get_serializer(requisition)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """API endpoint for persistent Purchase Orders."""

    # Uses project DEFAULT_AUTHENTICATION_CLASSES (Token + JWT)
    permission_classes = [IsAuthenticated]

    serializer_class = PurchaseOrderSerializer

    def get_permissions(self):
        return _get_permission_instances()

    def get_queryset(self):
        return (
            PurchaseOrder.objects.select_related("supplier", "requisition")
            .prefetch_related("items")
            .all()
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        created_by = None
        if self.request.user and self.request.user.is_authenticated:
            created_by = getattr(self.request.user, "username", None) or str(
                self.request.user
            )
        serializer.save(created_by=created_by)

    def update(self, request, *args, **kwargs):
        po: PurchaseOrder = self.get_object()
        if po.status in {"delivered", "cancelled"}:
            return Response(
                {
                    "detail": f"{po.status.capitalize()} purchase orders cannot be edited."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        po: PurchaseOrder = self.get_object()
        if po.status == "delivered":
            return Response(
                {"detail": "Delivered purchase orders cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="receive")
    def receive(self, request, *args, **kwargs):
        """Receive stock for this PO (atomic).

        - Marks PO as delivered
        - Updates linked InventoryItem stock (+quantity)
        - Writes StockMovement entries for audit
        """

        po: PurchaseOrder = self.get_object()
        if po.status == "delivered":
            return Response(
                {"detail": "Purchase order is already delivered."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if po.status == "cancelled":
            return Response(
                {"detail": "Cancelled purchase orders cannot be received."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        actor = (
            request.user.username
            if request.user and request.user.is_authenticated
            else "Anonymous"
        )

        with transaction.atomic():
            try:
                _receive_purchase_order_in_atomic(po, actor=actor)
            except Exception as exc:
                return Response(
                    {"detail": str(exc) or "Failed to receive purchase order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = self.get_serializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)
