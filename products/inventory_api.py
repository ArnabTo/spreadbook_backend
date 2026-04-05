from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
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
from .models.product_model import StockSummary
from .serializers import (
    InventoryItemSerializer,
    InventoryItemCreateUpdateSerializer,
    InventoryCategorySerializer,
    StockMovementSerializer,
    AddStockSerializer,
    InventoryStatsSerializer,
    StockSummaryInventorySerializer,
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


class StockSummaryInventoryView(APIView):
    """Inventory listing endpoint backed by StockSummary rows."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        branch_id = request.query_params.get("branch_id") or request.query_params.get(
            "branchId"
        )
        warehouse_id = request.query_params.get(
            "warehouse_id"
        ) or request.query_params.get("warehouseId")

        if not branch_id and not warehouse_id:
            return Response(
                {"error": "branch_id or warehouse_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if branch_id and not is_unrestricted_user(request.user):
            allowed_branch_ids = get_allowed_branch_ids_for_user(request.user)
            if allowed_branch_ids is not None and str(branch_id) not in {
                str(b) for b in allowed_branch_ids
            }:
                return Response(
                    {"error": "Access denied"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        qs = StockSummary.objects.select_related(
            "product",
            "product__unit",
            "product__display_unit",
            "product__unit_conversion_group",
            "product__selling_unit",
            "product__supplier",
            "product__generic_name",
            "product__brand",
            "variant",
        )

        if branch_id:
            qs = qs.filter(branch_id=branch_id, location="in_branch")
        else:
            qs = qs.filter(warehouse_id=warehouse_id, location="in_warehouse")

        search = request.query_params.get("search") or request.query_params.get("q")
        if search:
            qs = qs.filter(
                Q(product__name__icontains=search)
                | Q(product__code__icontains=search)
                | Q(product__sku__icontains=search)
                | Q(variant__size__icontains=search)
                | Q(variant__size_code__icontains=search)
            )

        category = request.query_params.get("category")
        if category:
            qs = qs.filter(
                Q(product__category__iexact=category)
                | Q(product__category_ref__name__iexact=category)
            )

        supplier = request.query_params.get("supplier")
        if supplier:
            qs = qs.filter(product__supplier_id=supplier)

        inventory_type = request.query_params.get(
            "inventoryType"
        ) or request.query_params.get("status")

        product_rows = {}
        for row in qs.order_by("product__name", "variant__size"):
            pid = str(row.product_id)
            product_entry = product_rows.get(pid)
            if product_entry is None:
                product_entry = {
                    "product": row.product,
                    "rows": [],
                    "current_stock": 0,
                }
                product_rows[pid] = product_entry

            product_entry["rows"].append(row)
            product_entry["current_stock"] += float(row.quantity or 0)

        def format_timestamp(value):
            if not value:
                return ""
            try:
                return value.isoformat()
            except Exception:
                return str(value)

        def derive_status(current_stock, threshold):
            if current_stock <= 0:
                return "out_of_stock"
            half_threshold = threshold // 2
            if current_stock <= half_threshold:
                return "critical"
            if current_stock <= threshold:
                return "low"
            if current_stock <= threshold * 2:
                return "medium"
            return "good"

        def to_status_display(status):
            return {
                "out_of_stock": "Out of Stock",
                "critical": "Critical Stock",
                "low": "Low Stock",
                "medium": "Medium Stock",
                "good": "In Stock",
            }.get(status, "In Stock")

        items = []
        for pid, group in product_rows.items():
            product = group["product"]
            current_stock = group["current_stock"]
            low_stock_threshold = int(product.low_stock_threshold or 20)
            max_stock = int(product.quantity or low_stock_threshold * 5 or 100)
            cost_per_unit = float(product.supplier_price or product.price or 0)
            stock_status = derive_status(current_stock, low_stock_threshold)
            status_display = to_status_display(stock_status)
            stock_percentage = (current_stock / max_stock) * 100 if max_stock > 0 else 0
            is_low_stock = stock_status in {"low", "critical", "out_of_stock"}

            variants = []
            for row in group["rows"]:
                if row.variant_id:
                    variants.append(
                        {
                            "id": str(row.variant_id),
                            "size": row.variant.size,
                            "size_name": row.variant.size_name,
                            "size_code": row.variant.size_code,
                            "size_qty": float(row.quantity or 0),
                            "color": row.variant.color,
                            "price": float(row.variant.price or 0),
                            "supplier_price": float(row.variant.supplier_price or 0),
                        }
                    )

            category_name = product.category or (
                product.category_ref.name
                if getattr(product, "category_ref", None)
                else ""
            )
            supplier_name = (
                getattr(product.supplier, "name", "") if product.supplier else ""
            )
            generic_name = (
                getattr(product.generic_name, "name", None)
                if product.generic_name
                else None
            )
            brand_name = getattr(product.brand, "name", None) if product.brand else None

            items.append(
                {
                    "id": str(product.id),
                    "product_id": str(product.id),
                    "name": product.name or "",
                    "category": product.category or "",
                    "category_name": category_name,
                    "unit": product.unit_id,
                    "unit_name": (
                        getattr(product.unit, "name", "") if product.unit else ""
                    ),
                    "current_stock": current_stock,
                    "reorder_level": low_stock_threshold,
                    "max_stock": max_stock,
                    "cost_per_unit": cost_per_unit,
                    "total_value": current_stock * cost_per_unit,
                    "supplier": product.supplier_id,
                    "supplier_name": supplier_name,
                    "status": stock_status,
                    "status_display": status_display,
                    "last_updated": format_timestamp(
                        product.updateAt or product.createdAt
                    ),
                    "formatted_last_updated": format_timestamp(
                        product.updateAt or product.createdAt
                    ),
                    "stock_percentage": stock_percentage,
                    "is_low_stock": is_low_stock,
                    "sku": product.sku,
                    "description": product.description or product.subDescription or "",
                    "location": None,
                    "expiry_date": getattr(product, "exp_date", None),
                    "warranty_expiry_date": None,
                    "notes": None,
                    "average_usage": None,
                    "inventoryType": product.inventoryType,
                    "low_stock_threshold": low_stock_threshold,
                    "generic_name": generic_name,
                    "brand_name": brand_name,
                    "secondary_unit": product.secondary_unit_id,
                    "secondary_unit_name": (
                        getattr(product.secondary_unit, "name", None)
                        if product.secondary_unit
                        else None
                    ),
                    "unit_conversion_factor": float(
                        product.unit_conversion_factor or 1
                    ),
                    "in_stock_secondary": float(product.in_stock_secondary or 0),
                    "unit_conversion_group": product.unit_conversion_group_id,
                    "unit_conversion_group_name": (
                        getattr(product.unit_conversion_group, "name", None)
                        if product.unit_conversion_group
                        else None
                    ),
                    "display_unit": product.display_unit_id,
                    "display_unit_name": (
                        getattr(product.display_unit, "name", None)
                        if product.display_unit
                        else None
                    ),
                    "selling_unit": product.selling_unit_id,
                    "selling_unit_name": (
                        getattr(product.selling_unit, "name", None)
                        if product.selling_unit
                        else None
                    ),
                    "selling_unit_conversion_factor": float(
                        product.selling_unit_conversion_factor or 1
                    ),
                    "price": float(product.price or 0),
                    "priceSale": float(product.priceSale or 0),
                    "regular_price": float(product.regular_price or 0),
                    "image": (
                        getattr(product.coverUrl, "name", None)
                        or getattr(product.image, "name", None)
                        if product.image or product.coverUrl
                        else None
                    ),
                    "quantity": int(product.quantity or 0),
                    "variants": variants,
                }
            )

        if inventory_type:
            inventory_type = (
                str(inventory_type).strip().lower().replace("_", " ").replace("-", " ")
            )
            mapped = inventory_type
            if mapped == "low stock":
                mapped = "low_stock"
            elif mapped == "out of stock":
                mapped = "out_of_stock"
            if mapped == "out_of_stock":
                items = [i for i in items if i["current_stock"] <= 0]
            elif mapped == "critical":
                items = [
                    i
                    for i in items
                    if i["current_stock"] > 0
                    and i["current_stock"] <= (i["reorder_level"] // 2)
                ]
            elif mapped == "low":
                items = [
                    i
                    for i in items
                    if i["current_stock"] > (i["reorder_level"] // 2)
                    and i["current_stock"] <= i["reorder_level"]
                ]
            elif mapped == "low_stock":
                items = [
                    i
                    for i in items
                    if i["current_stock"] > 0
                    and i["current_stock"] <= i["reorder_level"]
                ]
            elif mapped == "in stock":
                items = [i for i in items if i["current_stock"] > i["reorder_level"]]
            elif mapped == "medium":
                items = [
                    i
                    for i in items
                    if i["current_stock"] > i["reorder_level"]
                    and i["current_stock"] <= i["reorder_level"] * 2
                ]
            elif mapped == "good":
                items = [
                    i for i in items if i["current_stock"] > i["reorder_level"] * 2
                ]

        ordering = request.query_params.get("ordering")
        if ordering:
            descending = ordering.startswith("-")
            sort_field = ordering[1:] if descending else ordering
            valid_fields = {
                "name": lambda item: str(item.get("name") or "").lower(),
                "current_stock": lambda item: float(item.get("current_stock") or 0),
                "total_value": lambda item: float(item.get("total_value") or 0),
                "reorder_level": lambda item: float(item.get("reorder_level") or 0),
            }
            key = valid_fields.get(
                sort_field, lambda item: str(item.get("name") or "").lower()
            )
            items.sort(key=key, reverse=descending)
        else:
            items.sort(key=lambda item: str(item.get("name") or "").lower())

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(200, max(1, int(request.query_params.get("page_size", 80))))
        except (ValueError, TypeError):
            page = 1
            page_size = 80

        total = len(items)
        offset = (page - 1) * page_size
        paged_items = items[offset : offset + page_size]
        has_next = offset + page_size < total
        has_prev = page > 1

        summary = {
            "total_value": sum(float(i["total_value"] or 0) for i in paged_items),
            "low_stock_count": sum(
                1
                for i in paged_items
                if i["status"] in {"low", "critical", "out_of_stock"}
            ),
            "out_of_stock_count": sum(
                1 for i in paged_items if i["status"] == "out_of_stock"
            ),
            "in_stock_count": sum(1 for i in paged_items if i["current_stock"] > 0),
            "categories_count": len(
                {i["category_name"] for i in paged_items if i["category_name"]}
            ),
        }

        serializer = StockSummaryInventorySerializer(paged_items, many=True)
        return Response(
            {
                "count": total,
                "next": has_next,
                "previous": has_prev,
                "results": serializer.data,
                "summary": summary,
            }
        )


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
