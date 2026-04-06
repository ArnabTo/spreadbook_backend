from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import PurchaseOrder, PurchaseOrderItem, PurchaseRequisition, QuickPurchase
from .serializers import (
    PurchaseOrderSerializer,
    PurchaseRequisitionSerializer,
    QuickPurchaseSerializer,
    QuickPurchaseConvertSerializer,
)


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
    from products.models.product_model import Product, StockSummary

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

                # Update StockSummary for this product/variant
                try:
                    product_obj = (
                        Product.objects.filter(pk=it.product_id)
                        .select_related("companyId")
                        .first()
                    )
                    if product_obj:
                        warehouse = po.warehouse or product_obj.warehouse
                        branch = po.branch
                        location = "in_branch" if branch else "in_warehouse"
                        ss, _ = StockSummary.objects.get_or_create(
                            product=product_obj,
                            variant=it.variant if it.variant_id else None,
                            warehouse=None if branch else warehouse,
                            branch=branch,
                            location=location,
                            defaults={
                                "company": product_obj.companyId,
                                "quantity": 0,
                            },
                        )
                        ss.quantity = F("quantity") + qty_int
                        ss.save(update_fields=["quantity"])
                except Exception as e:
                    # Non-fatal: stock summary update failure should not block receive
                    import logging

                    logging.getLogger(__name__).warning(
                        "StockSummary update failed for product %s during PO %s receive: %s",
                        it.product_id,
                        po.po_number,
                        e,
                    )

    po.status = "delivered"
    po.save(update_fields=["status", "updated_at"])

    if po.requisition_id and po.requisition.status == "approved":
        po.requisition.status = "converted"
        po.requisition.save(update_fields=["status", "updated_at"])


def _create_purchase_order_for_requisition(
    requisition: PurchaseRequisition, actor: str, company=None
) -> PurchaseOrder:
    items = requisition.items.select_related("product", "inventory_item").all()
    if not items.exists():
        raise ValueError("Requisition has no items.")

    po = PurchaseOrder.objects.create(
        requisition=requisition,
        supplier=None,
        status="pending",
        notes=f"Auto-created from {requisition.pr_number}",
        created_by=actor,
        companyId=company,
    )

    for it in items:
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=(
                it.product if requisition.purchase_type == "direct_inventory" else None
            ),
            inventory_item=(
                it.inventory_item
                if requisition.purchase_type != "direct_inventory"
                else None
            ),
            name=it.item_name,
            quantity=it.quantity,
            unit=it.unit,
            unit_price=Decimal("0"),
        )

    po.recalc_total()
    return po


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
        incoming_status = None
        if hasattr(request.data, "get"):
            incoming_status = request.data.get("status")
        elif isinstance(request.data, dict):
            incoming_status = request.data.get("status")

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

        with transaction.atomic():
            response = super().partial_update(request, *args, **kwargs)
            if (
                incoming_status == "approved"
                and requisition.status != "approved"
                and self.get_object().status == "approved"
            ):
                actor = (
                    request.user.username
                    if request.user and request.user.is_authenticated
                    else "Anonymous"
                )
                company = getattr(request.user, "companyId", None) or getattr(
                    request.user, "company", None
                )
                _create_purchase_order_for_requisition(
                    self.get_object(), actor, company=company
                )
            return response

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

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, *args, **kwargs):
        """Approve a pending purchase order."""
        po: PurchaseOrder = self.get_object()
        if po.status != "pending":
            return Response(
                {
                    "detail": f"Only pending POs can be approved. Current status: {po.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        po.status = "approved"
        po.save(update_fields=["status", "updated_at"])
        serializer = self.get_serializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="mark-waiting")
    def mark_waiting_for_receive(self, request, *args, **kwargs):
        """Move an approved PO to 'Waiting for Receive' state."""
        po: PurchaseOrder = self.get_object()
        if po.status != "approved":
            return Response(
                {
                    "detail": f"Only approved POs can be marked as waiting for receive. Current status: {po.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        po.status = "waiting_for_receive"
        po.save(update_fields=["status", "updated_at"])
        serializer = self.get_serializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, *args, **kwargs):
        """Cancel a purchase order."""
        po: PurchaseOrder = self.get_object()
        if po.status == "delivered":
            return Response(
                {"detail": "Delivered purchase orders cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        po.status = "cancelled"
        po.save(update_fields=["status", "updated_at"])
        serializer = self.get_serializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)


class QuickPurchaseViewSet(viewsets.ModelViewSet):
    """Immediate buy records and conversion into Product stock."""

    permission_classes = [IsAuthenticated]
    serializer_class = QuickPurchaseSerializer
    queryset = QuickPurchase.objects.all().order_by("-created_at")

    def get_permissions(self):
        return _get_permission_instances()

    def get_queryset(self):
        # Keep consistent with other APIs: apply company/branch scoping when available.
        from common.drf_scoping import apply_company_branch_scope

        qs = super().get_queryset()
        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

    def perform_create(self, serializer):
        # Auto-calc remaining_qty.
        data = serializer.validated_data
        purchased = int(data.get("qty_purchased") or 0)
        sold = int(data.get("qty_sold") or 0)
        remaining = max(purchased - sold, 0)

        # Capture company/branch from request user when available.
        company = getattr(self.request.user, "companyId", None)
        branch = None
        if (
            hasattr(self.request.user, "branchAccess")
            and self.request.user.branchAccess.exists()
        ):
            branch = self.request.user.branchAccess.first()

        serializer.save(
            remaining_qty=remaining,
            companyId=company,
            branch=branch,
        )

    @action(detail=True, methods=["post"], url_path="convert-to-product")
    def convert_to_product(self, request, pk=None):
        """Convert remaining qty into a Product row with stock, so it appears in Product list."""

        from django.db import transaction
        from products.models.product_model import Product

        qp: QuickPurchase = self.get_object()
        if qp.status != "pending":
            return Response(
                {"error": "Only pending quick purchases can be converted"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        remaining = int(qp.remaining_qty or 0)
        if remaining <= 0:
            return Response(
                {"error": "No remaining quantity to add to product list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = QuickPurchaseConvertSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        v = payload.validated_data

        name = (v.get("name") or qp.name or "").strip() or qp.name
        category = (v.get("category") or qp.category or "").strip()
        code = v.get("code") if "code" in v else qp.code
        sku = v.get("sku") if "sku" in v else qp.sku

        with transaction.atomic():
            # Create a Product (new catalog item). We intentionally do NOT attempt
            # to auto-merge by name to avoid accidentally mixing different items.
            product = Product.objects.create(
                companyId=qp.companyId,
                branch=qp.branch,
                name=name,
                category=category or "products",
                code=(
                    str(code).strip()
                    if code is not None and str(code).strip()
                    else None
                ),
                sku=(
                    str(sku).strip() if sku is not None and str(sku).strip() else None
                ),
                price=float(qp.unit_price or 0),
                in_stock=remaining,
                quantity=remaining,
                totalPurchase=remaining,
                out_of_stock=False,
                status="in stock",
                inventoryType="in stock",
                available=remaining,
            )

            qp.product = product
            qp.status = "converted"
            qp.save(update_fields=["product", "status", "updated_at"])

        return Response(QuickPurchaseSerializer(qp).data, status=status.HTTP_200_OK)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """API endpoint for persistent Purchase Orders."""

    # Uses project DEFAULT_AUTHENTICATION_CLASSES (Token + JWT)
    permission_classes = [IsAuthenticated]

    serializer_class = PurchaseOrderSerializer

    def get_permissions(self):
        return _get_permission_instances()

    def get_queryset(self):
        qs = (
            PurchaseOrder.objects.select_related(
                "supplier", "requisition", "branch", "warehouse", "companyId"
            )
            .prefetch_related(
                "items__product", "items__variant", "items__inventory_item"
            )
            .all()
            .order_by("-created_at")
        )

        supplier_id = self.request.query_params.get(
            "supplier"
        ) or self.request.query_params.get("supplier_id")
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)

        branch_id = self.request.query_params.get(
            "branch"
        ) or self.request.query_params.get("branch_id")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        warehouse_id = self.request.query_params.get(
            "warehouse"
        ) or self.request.query_params.get("warehouse_id")
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)

        company_id = (
            self.request.query_params.get("company")
            or self.request.query_params.get("company_id")
            or self.request.query_params.get("companyId")
        )
        if company_id:
            qs = qs.filter(companyId_id=company_id)

        po_status = self.request.query_params.get("status")
        if po_status:
            qs = qs.filter(status=po_status)

        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            is_unrestricted = bool(getattr(user, "is_superuser", False)) or getattr(
                user, "role", None
            ) in ("software_owner", "super_admin", "admin")
            if not is_unrestricted:
                allowed_branch_ids = set()
                if hasattr(user, "branchAccess") and user.branchAccess.exists():
                    allowed_branch_ids.update(
                        user.branchAccess.values_list("id", flat=True)
                    )

                if allowed_branch_ids:
                    if branch_id and str(branch_id) not in {
                        str(bid) for bid in allowed_branch_ids
                    }:
                        raise PermissionDenied("You do not have access to this branch")
                    qs = qs.filter(branch_id__in=allowed_branch_ids)
                elif getattr(user, "companyId_id", None):
                    qs = qs.filter(companyId_id=user.companyId_id)
                else:
                    qs = qs.none()

        return qs

    def perform_create(self, serializer):
        created_by = None
        branch_id = self.request.data.get("branch") or self.request.data.get(
            "branch_id"
        )
        warehouse_id = self.request.data.get("warehouse") or self.request.data.get(
            "warehouse_id"
        )
        company_id = self.request.data.get("companyId") or self.request.data.get(
            "company_id"
        )

        if self.request.user and self.request.user.is_authenticated:
            is_unrestricted = bool(
                getattr(self.request.user, "is_superuser", False)
            ) or getattr(self.request.user, "role", None) in (
                "software_owner",
                "super_admin",
                "admin",
            )
            created_by = getattr(self.request.user, "username", None) or str(
                self.request.user
            )
            if (
                not branch_id
                and not warehouse_id
                and hasattr(self.request.user, "branchAccess")
            ):
                default_branch = self.request.user.branchAccess.first()
                if default_branch:
                    branch_id = default_branch.id

            if (
                branch_id
                and not is_unrestricted
                and hasattr(self.request.user, "branchAccess")
            ):
                allowed_branch_ids = set(
                    self.request.user.branchAccess.values_list("id", flat=True)
                )
                if allowed_branch_ids and str(branch_id) not in {
                    str(bid) for bid in allowed_branch_ids
                }:
                    raise PermissionDenied("You do not have access to this branch")

            # Auto-assign company from user if not provided
            if not company_id and getattr(self.request.user, "companyId_id", None):
                company_id = self.request.user.companyId_id

        save_kwargs = {"created_by": created_by}
        if branch_id:
            save_kwargs["branch_id"] = branch_id
        if warehouse_id:
            save_kwargs["warehouse_id"] = warehouse_id
        if company_id:
            save_kwargs["companyId_id"] = company_id

        serializer.save(**save_kwargs)

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

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, *args, **kwargs):
        """Approve a pending purchase order."""
        po: PurchaseOrder = self.get_object()
        if po.status != "pending":
            return Response(
                {
                    "detail": f"Only pending POs can be approved. Current status: {po.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        po.status = "approved"
        po.save(update_fields=["status", "updated_at"])
        serializer = self.get_serializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="mark-waiting")
    def mark_waiting_for_receive(self, request, *args, **kwargs):
        """Move an approved PO to waiting_for_receive state."""
        po: PurchaseOrder = self.get_object()
        if po.status != "approved":
            return Response(
                {
                    "detail": f"Only approved POs can be marked as waiting for receive. Current status: {po.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        po.status = "waiting_for_receive"
        po.save(update_fields=["status", "updated_at"])
        serializer = self.get_serializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)

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

    # ── Goods Receipt / Barcode Scan endpoints ─────────────────────────────────

    @action(detail=True, methods=["get"], url_path="serial-items")
    def serial_items(self, request, *args, **kwargs):
        """Return pending and received serial items for this PO.

        First tries the direct FK (purchase_order=po). Falls back to matching
        by the products/variants listed in PO items (for legacy/unlinked items).
        """
        from products.models.product_model import ProductSerialItem
        from products.serializers import ProductSerialItemSerializer
        from django.db.models import Q

        po = self.get_object()

        # Primary: items directly linked via FK
        qs = ProductSerialItem.objects.select_related(
            "product", "variant", "warehouse", "branch"
        ).filter(purchase_order=po)

        # Fallback: match by products/variants in PO items
        if not qs.exists():
            product_ids = list(
                po.items.exclude(product__isnull=True).values_list(
                    "product_id", flat=True
                )
            )
            variant_ids = list(
                po.items.exclude(variant__isnull=True).values_list(
                    "variant_id", flat=True
                )
            )
            if product_ids or variant_ids:
                qs = ProductSerialItem.objects.select_related(
                    "product", "variant", "warehouse", "branch"
                ).filter(Q(product_id__in=product_ids) | Q(variant_id__in=variant_ids))

        pending = qs.exclude(status="received")
        received = qs.filter(status="received")
        total = qs.count()
        received_count = received.count()

        return Response(
            {
                "pending": ProductSerialItemSerializer(pending, many=True).data,
                "received": ProductSerialItemSerializer(received, many=True).data,
                "total": total,
                "received_count": received_count,
                "all_received": total > 0 and received_count == total,
            }
        )

    @action(detail=True, methods=["post"], url_path="scan-item")
    def scan_item(self, request, *args, **kwargs):
        """Scan a serial code to mark one item as received.

        Optimized: single item lookup + bulk check done in one queryset count.
        Returns updated counts and whether the PO is now complete.
        """
        from products.models.product_model import ProductSerialItem
        from products.serializers import ProductSerialItemSerializer
        from django.db.models import Q

        po = self.get_object()
        if po.status != "waiting_for_receive":
            return Response(
                {"detail": "PO must be in 'waiting for receive' status to scan items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serial_code = (request.data.get("serial_code") or "").strip()
        if not serial_code:
            return Response(
                {"detail": "serial_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            item = ProductSerialItem.objects.select_related("product", "variant").get(
                serial_code=serial_code
            )
        except ProductSerialItem.DoesNotExist:
            return Response(
                {"detail": f"No item found with serial code '{serial_code}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if item.status == "received":
            return Response(
                {
                    "detail": "This item has already been received.",
                    "already_received": True,
                },
                status=status.HTTP_200_OK,
            )

        # Verify item belongs to this PO — direct FK or product/variant match
        product_ids = set(
            po.items.exclude(product__isnull=True).values_list("product_id", flat=True)
        )
        variant_ids = set(
            po.items.exclude(variant__isnull=True).values_list("variant_id", flat=True)
        )
        belongs = (
            item.purchase_order_id == po.uuid
            or item.product_id in product_ids
            or item.variant_id in variant_ids
        )
        if not belongs:
            return Response(
                {"detail": "This item does not belong to this purchase order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark received and link to this PO
        item.status = "received"
        item.purchase_order = po
        item.save(update_fields=["status", "purchase_order", "updated_at"])

        # Check completion: count all items covering this PO's products/variants
        scope_qs = ProductSerialItem.objects.filter(
            Q(purchase_order=po)
            | Q(product_id__in=product_ids)
            | Q(variant_id__in=variant_ids)
        ).distinct()
        total = scope_qs.count()
        pending_count = scope_qs.exclude(status="received").count()
        po_completed = total > 0 and pending_count == 0

        if po_completed:
            po.status = "delivered"
            po.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "serial_item": ProductSerialItemSerializer(item).data,
                "pending_count": pending_count,
                "received_count": total - pending_count,
                "total": total,
                "po_completed": po_completed,
            }
        )

    @action(detail=True, methods=["post"], url_path="receive-all")
    def receive_all(self, request, *args, **kwargs):
        """Mark ALL pending serial items for this PO as received at once."""
        from products.models.product_model import ProductSerialItem
        from django.db.models import Q

        po = self.get_object()
        if po.status != "waiting_for_receive":
            return Response(
                {"detail": "PO must be in 'waiting for receive' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product_ids = set(
            po.items.exclude(product__isnull=True).values_list("product_id", flat=True)
        )
        variant_ids = set(
            po.items.exclude(variant__isnull=True).values_list("variant_id", flat=True)
        )

        scope_qs = ProductSerialItem.objects.filter(
            Q(purchase_order=po)
            | Q(product_id__in=product_ids)
            | Q(variant_id__in=variant_ids)
        ).distinct()

        pending = scope_qs.exclude(status="received")
        updated_count = pending.update(
            status="received",
            purchase_order=po,
        )

        po.status = "delivered"
        po.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "updated_count": updated_count,
                "po_completed": True,
            }
        )
