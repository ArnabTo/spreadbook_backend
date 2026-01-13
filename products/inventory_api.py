from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F
from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend

from common.drf_scoping import (
    is_unrestricted_user,
    get_company_ids_for_user,
    get_allowed_branch_ids_for_user,
)
from rest_framework.exceptions import PermissionDenied
from company.models import Branch

from .models.inventory_model import InventoryItem, InventoryCategory, StockMovement
from .serializers import (
    InventoryItemSerializer,
    InventoryItemCreateUpdateSerializer,
    InventoryCategorySerializer,
    StockMovementSerializer,
    AddStockSerializer,
    InventoryStatsSerializer,
)


class InventoryCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing inventory categories"""

    queryset = InventoryCategory.objects.filter(is_active=True)
    serializer_class = InventoryCategorySerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        qs = InventoryCategory.objects.filter(is_active=True)

        user = getattr(self.request, "user", None)
        if not user or is_unrestricted_user(user):
            return qs

        company_ids = get_company_ids_for_user(user)
        if not company_ids:
            return qs.none()

        # Include legacy rows where companyId is NULL.
        return qs.filter(
            Q(companyId_id__in=list(company_ids)) | Q(companyId_id__isnull=True)
        ).distinct()

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        if not user or is_unrestricted_user(user):
            serializer.save()
            return

        # Prefer explicit user.companyId; categories are company-level (branch not applicable).
        serializer.save(companyId=getattr(user, "companyId", None))


class InventoryItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing inventory items"""

    queryset = InventoryItem.objects.select_related(
        "category", "unit", "supplier", "branch", "companyId"
    ).all()
    serializer_class = InventoryItemSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category", "supplier", "status"]
    search_fields = ["name", "sku", "description"]
    ordering_fields = [
        "name",
        "current_stock",
        "last_updated",
        "cost_per_unit",
        "total_value",
        "status",
    ]
    ordering = ["name"]

    def get_queryset(self):
        qs = InventoryItem.objects.select_related(
            "category",
            "unit",
            "supplier",
            "branch",
            "companyId",
        ).all()

        user = getattr(self.request, "user", None)
        if not user or is_unrestricted_user(user):
            return qs

        company_ids = get_company_ids_for_user(user)
        if not company_ids:
            return qs.none()

        # Company scope + include legacy NULL companyId.
        qs = qs.filter(
            Q(companyId_id__in=list(company_ids)) | Q(companyId_id__isnull=True)
        )

        # Branch scope: only when explicit access exists.
        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if allowed_branch_ids is not None:
            requested_branch_id = self.request.query_params.get(
                "branch_id"
            ) or self.request.query_params.get("branchId")
            if requested_branch_id:
                if str(requested_branch_id) not in allowed_branch_ids:
                    raise PermissionDenied("You do not have access to this branch")
                qs = qs.filter(branch_id=requested_branch_id)
            else:
                qs = qs.filter(
                    Q(branch_id__in=list(allowed_branch_ids))
                    | Q(branch_id__isnull=True)
                )

        return qs.distinct()

    def _resolve_company_and_branch_for_write(self):
        """Resolve (company, branch) for create/update.

        - If branch_id is provided, validate access and derive company from branch.
        - Else fall back to request.user.companyId (company-wide).
        """

        user = getattr(self.request, "user", None)
        if not user or is_unrestricted_user(user):
            return (None, None)

        requested_branch_id = self.request.query_params.get(
            "branch_id"
        ) or self.request.query_params.get("branchId")

        if requested_branch_id:
            allowed_branch_ids = get_allowed_branch_ids_for_user(user)
            if (
                allowed_branch_ids is not None
                and str(requested_branch_id) not in allowed_branch_ids
            ):
                raise PermissionDenied("You do not have access to this branch")

            branch = (
                Branch.objects.filter(id=requested_branch_id)
                .select_related("company")
                .first()
            )
            if not branch:
                raise PermissionDenied("Invalid branch")

            return (branch.company, branch)

        return (getattr(user, "companyId", None), None)

    def perform_create(self, serializer):
        company, branch = self._resolve_company_and_branch_for_write()
        serializer.save(companyId=company, branch=branch)

    def perform_update(self, serializer):
        company, branch = self._resolve_company_and_branch_for_write()
        # Preserve existing company/branch if caller didn't provide branch_id.
        if company is None and branch is None:
            serializer.save()
            return
        serializer.save(companyId=company, branch=branch)

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return InventoryItemCreateUpdateSerializer
        return InventoryItemSerializer

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """Get items with low stock (at or below reorder level)"""
        low_stock_items = self.get_queryset().filter(
            current_stock__lte=F("reorder_level")
        )
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get inventory statistics"""
        qs = self.get_queryset()

        total_items = qs.count()
        low_stock_count = qs.filter(current_stock__lte=F("reorder_level")).count()
        out_of_stock_count = qs.filter(current_stock__lte=0).count()
        total_value = qs.aggregate(total=Sum("total_value"))["total"] or Decimal("0.00")

        categories_qs = InventoryCategory.objects.filter(is_active=True)
        user = getattr(request, "user", None)
        if user and not is_unrestricted_user(user):
            company_ids = get_company_ids_for_user(user)
            if company_ids:
                categories_qs = categories_qs.filter(
                    Q(companyId_id__in=list(company_ids)) | Q(companyId_id__isnull=True)
                )
            else:
                categories_qs = categories_qs.none()

        categories_count = categories_qs.count()

        stats_data = {
            "total_items": total_items,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "total_value": total_value,
            "categories_count": categories_count,
        }

        serializer = InventoryStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_stock(self, request, pk=None):
        """Add stock to an inventory item"""
        inventory_item = self.get_object()
        serializer = AddStockSerializer(data=request.data)

        if serializer.is_valid():
            quantity = serializer.validated_data["quantity"]
            reason = serializer.validated_data.get("reason", "Stock addition")
            notes = serializer.validated_data.get("notes", "")
            reference_number = serializer.validated_data.get("reference_number", "")
            expiry_date = serializer.validated_data.get("expiry_date")
            warranty_expiry_date = serializer.validated_data.get("warranty_expiry_date")

            # Record previous stock
            previous_stock = inventory_item.current_stock

            # Update stock
            inventory_item.current_stock += quantity

            # Optional metadata updates
            if expiry_date is not None:
                inventory_item.expiry_date = expiry_date
            if warranty_expiry_date is not None:
                inventory_item.warranty_expiry_date = warranty_expiry_date

            inventory_item.save()

            # Create stock movement record
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type="in",
                quantity=quantity,
                previous_stock=previous_stock,
                new_stock=inventory_item.current_stock,
                reason=reason,
                notes=notes,
                reference_number=reference_number,
                created_by=(
                    request.user.username
                    if request.user.is_authenticated
                    else "Anonymous"
                ),
            )

            # Return updated item
            serializer = self.get_serializer(inventory_item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reduce_stock(self, request, pk=None):
        """Reduce stock from an inventory item"""
        inventory_item = self.get_object()
        serializer = AddStockSerializer(data=request.data)

        if serializer.is_valid():
            quantity = serializer.validated_data["quantity"]
            reason = serializer.validated_data.get("reason", "Stock reduction")
            notes = serializer.validated_data.get("notes", "")
            reference_number = serializer.validated_data.get("reference_number", "")
            expiry_date = serializer.validated_data.get("expiry_date")
            warranty_expiry_date = serializer.validated_data.get("warranty_expiry_date")

            # Check if enough stock available
            if inventory_item.current_stock < quantity:
                return Response(
                    {
                        "error": f"Insufficient stock. Available: {inventory_item.current_stock}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Record previous stock
            previous_stock = inventory_item.current_stock

            # Update stock
            inventory_item.current_stock -= quantity

            # Optional metadata updates
            if expiry_date is not None:
                inventory_item.expiry_date = expiry_date
            if warranty_expiry_date is not None:
                inventory_item.warranty_expiry_date = warranty_expiry_date

            inventory_item.save()

            # Create stock movement record
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type="out",
                quantity=quantity,
                previous_stock=previous_stock,
                new_stock=inventory_item.current_stock,
                reason=reason,
                notes=notes,
                reference_number=reference_number,
                created_by=(
                    request.user.username
                    if request.user.is_authenticated
                    else "Anonymous"
                ),
            )

            # Return updated item
            serializer = self.get_serializer(inventory_item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        """Get stock movements for an inventory item"""
        inventory_item = self.get_object()
        movements = StockMovement.objects.filter(inventory_item=inventory_item)
        serializer = StockMovementSerializer(movements, many=True)
        return Response(serializer.data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing stock movements (read-only)"""

    queryset = StockMovement.objects.select_related("inventory_item").all()
    serializer_class = StockMovementSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = StockMovement.objects.select_related(
            "inventory_item",
            "inventory_item__branch",
            "inventory_item__companyId",
        ).all()

        user = getattr(self.request, "user", None)
        if not user or is_unrestricted_user(user):
            return qs

        company_ids = get_company_ids_for_user(user)
        if not company_ids:
            return qs.none()

        qs = qs.filter(
            Q(inventory_item__companyId_id__in=list(company_ids))
            | Q(inventory_item__companyId_id__isnull=True)
        )

        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if allowed_branch_ids is not None:
            requested_branch_id = self.request.query_params.get(
                "branch_id"
            ) or self.request.query_params.get("branchId")
            if requested_branch_id:
                if str(requested_branch_id) not in allowed_branch_ids:
                    raise PermissionDenied("You do not have access to this branch")
                qs = qs.filter(inventory_item__branch_id=requested_branch_id)
            else:
                qs = qs.filter(
                    Q(inventory_item__branch_id__in=list(allowed_branch_ids))
                    | Q(inventory_item__branch_id__isnull=True)
                )

        return qs.distinct()
