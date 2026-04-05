from rest_framework.decorators import permission_classes, action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, viewsets, permissions, status, parsers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.timezone import get_default_timezone, is_naive, make_aware
from datetime import datetime, time
from django.db.models import Q, Prefetch, Sum, Value
from django.db.models.functions import Coalesce
from django.db import transaction

from .models.category_model import Category
from .models.product_model import (
    Product,
    Image,
    NewLabel,
    SaleLabel,
    Size,
    Color,
    ProductVariant,
    ProductSerialItem,
    StockSummary,
    UnitConversionGroup,
    UnitConversionStep,
)
from .models import ProductType, GenericName, Brand, ProductBarcode, ProductBatch
from .models.stock_transfer_model import StockTransfer, StockTransferItem
from .models.unit_model import Unit
from .pagination import ProductPagination
from .filters import ProductFilter
from .serializers import (
    ProductSerializer,
    ProductPostSerializer,
    PictureSerializer,
    NewLavelSerializer,
    SaleLavelSerializer,
)
from .serializers import CategorySerializer, ColorSerializer, SizeSerializer
from .serializers import (
    ProductTypeSerializer,
    GenericNameSerializer,
    BrandSerializer,
    ProductBarcodeSerializer,
    ProductBatchSerializer,
)
from .serializers import UnitSerializer
from .serializers import UnitConversionGroupSerializer, UnitConversionStepSerializer


from rest_framework import generics
from django.shortcuts import render

from common.drf_scoping import (
    apply_company_branch_scope,
    is_unrestricted_user,
    get_company_ids_for_user,
    get_allowed_branch_ids_for_user,
)
from rest_framework.exceptions import PermissionDenied

from decimal import Decimal
import logging

from products.branch_inventory import (
    resolve_branch_from_request,
    adjust_branch_stock,
    update_branch_fields,
)

from .models.inventory_model import ProductStockMovement
from .serializers import (
    AddStockSerializer,
    ProductStockMovementSerializer,
    ProductSerialItemSerializer,
)
from .serializers import StockTransferSerializer, StockTransferCreateSerializer
from .serializers import StockSummaryPOSSerializer

logger = logging.getLogger(__name__)


class ProductOptionsView(APIView):
    """Return lightweight dropdown options for Product creation/edit forms.

    Keeps frontend fast by fetching types/brands/generic names in one request.
    """

    def get(self, request):
        # Company-scoped querysets (branch not applicable for these master-data tables)
        types_qs = apply_company_branch_scope(
            request=request,
            queryset=ProductType.objects.filter(is_active=True),
            company_id_field="companyId_id",
            branch_id_field=None,
        ).order_by("name")

        brands_qs = apply_company_branch_scope(
            request=request,
            queryset=Brand.objects.filter(is_active=True),
            company_id_field="companyId_id",
            branch_id_field=None,
        ).order_by("name")

        generics_qs = apply_company_branch_scope(
            request=request,
            queryset=GenericName.objects.filter(is_active=True),
            company_id_field="companyId_id",
            branch_id_field=None,
        ).order_by("name")

        categories_qs = apply_company_branch_scope(
            request=request,
            queryset=Category.objects.filter(is_active=True),
            company_id_field="companyId_id",
            branch_id_field=None,
        ).order_by("name")
        units_qs = Unit.objects.filter(status=True).order_by("name")

        return Response(
            {
                "categories": CategorySerializer(categories_qs, many=True).data,
                "units": UnitSerializer(units_qs, many=True).data,
                "types": ProductTypeSerializer(types_qs, many=True).data,
                "brands": BrandSerializer(brands_qs, many=True).data,
                "generic_names": GenericNameSerializer(generics_qs, many=True).data,
            }
        )


class UnitViewSet(viewsets.ModelViewSet):
    """CRUD for Unit.  Used by the frontend Add-Product form to create missing units."""

    serializer_class = UnitSerializer
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        return Unit.objects.all().order_by("name")

    def create(self, request, *args, **kwargs):
        # Normalise name: strip whitespace, reject blank.
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response(
                {"name": ["Unit name is required."]}, status=status.HTTP_400_BAD_REQUEST
            )

        # Return existing unit if name already taken (case-insensitive), so the
        # frontend can simply auto-select it without special-casing duplicates.
        existing = Unit.objects.filter(name__iexact=name).first()
        if existing:
            return Response(UnitSerializer(existing).data, status=status.HTTP_200_OK)

        unit = Unit.objects.create(name=name, status=True)
        return Response(UnitSerializer(unit).data, status=status.HTTP_201_CREATED)


class UnitConversionGroupViewSet(viewsets.ModelViewSet):
    """CRUD for reusable unit conversion rule groups."""

    serializer_class = UnitConversionGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):

        queryset = (
            UnitConversionGroup.objects.select_related("base_unit")
            .prefetch_related(
                "steps",
                "steps__from_unit",
                "steps__to_unit",
            )
            .order_by("name")
        )

        query_params = self.request.query_params

        unit_conversion_group_id = query_params.get("unit-conversion-groups-id")
        print("unit_conversion_group_id:", unit_conversion_group_id)
        if unit_conversion_group_id:
            queryset = queryset.filter(id=unit_conversion_group_id)

        return queryset


class UnitConversionStepViewSet(viewsets.ModelViewSet):
    """CRUD for conversion steps inside a unit conversion group."""

    serializer_class = UnitConversionStepSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        qs = UnitConversionStep.objects.select_related("group", "from_unit", "to_unit")
        group_id = self.request.query_params.get("group")
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs.order_by("group_id", "level")


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for product categories with company-scoped access"""

    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "is_active"]
    ordering = ["name"]

    def _is_unrestricted_user(self, user) -> bool:
        return (
            bool(getattr(user, "is_superuser", False))
            or getattr(user, "role", None) == "software_owner"
        )

    def _resolve_company(self, user):
        if getattr(user, "companyId", None):
            return user.companyId
        # Fallback: infer company from branch access if possible
        branches = user.branchAccess.select_related("company")
        company_ids = set(branches.values_list("company_id", flat=True))
        if len(company_ids) == 1 and branches.exists():
            return branches.first().company
        return None

    def _get_allowed_branch_ids(self, user):
        if self._is_unrestricted_user(user):
            return None
        if user.branchAccess.exists():
            return set(user.branchAccess.values_list("id", flat=True))
        return None

    def _resolve_company_from_branch(self, user):
        """Resolve company from branch_id query param"""
        from company.models import Branch

        branch_id = self.request.data.get("branch_id") or self.request.query_params.get(
            "branch_id"
        )
        if not branch_id:
            return None

        allowed_branch_ids = self._get_allowed_branch_ids(user)
        if allowed_branch_ids is not None and str(branch_id) not in {
            str(b) for b in allowed_branch_ids
        }:
            raise PermissionDenied("You do not have access to this branch")

        branch = Branch.objects.select_related("company").filter(id=branch_id).first()
        if not branch:
            raise PermissionDenied("Invalid branch_id")

        return branch.company

    def get_queryset(self):
        user = self.request.user
        queryset = Category.objects.select_related("companyId").prefetch_related(
            "branchId"
        )

        # Check if branch_id is provided
        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            company_from_branch = self._resolve_company_from_branch(user)
            if company_from_branch:
                return queryset.filter(companyId=company_from_branch, is_active=True)

        # Standard company scoping
        if not self._is_unrestricted_user(user):
            company_ids = set()
            if getattr(user, "companyId_id", None):
                company_ids.add(user.companyId_id)
            else:
                company_ids.update(
                    user.branchAccess.values_list("company_id", flat=True)
                )

            if not company_ids:
                return Category.objects.none()

            queryset = queryset.filter(companyId_id__in=company_ids)

        return queryset.filter(is_active=True)

    def perform_create(self, serializer):
        """Auto-assign company from selected branch, fallback to authenticated user company"""
        user = self.request.user
        company = self._resolve_company_from_branch(user) or self._resolve_company(user)

        if not company:
            raise PermissionDenied(
                "Unable to determine company. Provide a valid branch_id or ensure user has company access"
            )

        serializer.save(companyId=company)


class ColorViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = ColorSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return Color.objects.all()


class SizeViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = SizeSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return Size.objects.all()


class ProductTypeViewSet(viewsets.ModelViewSet):
    serializer_class = ProductTypeSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "createdAt", "updatedAt"]
    ordering = ["name"]

    def get_queryset(self):
        qs = ProductType.objects.all()
        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field=None,
        )

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        if user and not is_unrestricted_user(user):
            serializer.save(companyId=getattr(user, "companyId", None))
            return
        serializer.save()


class GenericNameViewSet(viewsets.ModelViewSet):
    serializer_class = GenericNameSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "createdAt", "updatedAt"]
    ordering = ["name"]

    def _resolve_company_from_branch(self, user):
        """Resolve company from branch_id query/body param, with access validation."""
        from company.models import Branch
        from rest_framework.exceptions import PermissionDenied

        branch_id = self.request.query_params.get("branch_id") or self.request.data.get(
            "branch_id"
        )
        if not branch_id:
            return None

        # For non-superusers validate branch access
        if not is_unrestricted_user(user):
            allowed = set()
            if hasattr(user, "branchAccess") and user.branchAccess.exists():
                allowed = set(
                    str(b) for b in user.branchAccess.values_list("id", flat=True)
                )
                if allowed and str(branch_id) not in allowed:
                    raise PermissionDenied("You do not have access to this branch")

        branch = Branch.objects.select_related("company").filter(id=branch_id).first()
        if branch:
            return branch.company
        return None

    def get_queryset(self):
        user = self.request.user
        qs = GenericName.objects.filter(is_active=True)

        # When branch_id is provided in the request, resolve the company from the
        # branch and scope to that company — this applies even for superusers so
        # that the UI only shows the currently-selected company's generic names.
        company = self._resolve_company_from_branch(user)
        if company is not None:
            return qs.filter(companyId=company)

        # Standard company scoping for regular users (superusers see all)
        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field=None,
        )

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        if user and not is_unrestricted_user(user):
            company = getattr(user, "companyId", None)
            if company is None:
                company = self._resolve_company_from_branch(user)
            serializer.save(companyId=company)
            return
        # For superusers, still try to scope to the branch's company if provided
        company = self._resolve_company_from_branch(user)
        if company is not None:
            serializer.save(companyId=company)
        else:
            serializer.save()


class BrandViewSet(viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "createdAt", "updatedAt"]
    ordering = ["name"]

    def get_queryset(self):
        qs = Brand.objects.all()
        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field=None,
        )

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        if user and not is_unrestricted_user(user):
            serializer.save(companyId=getattr(user, "companyId", None))
            return
        serializer.save()


class ProductBarcodeViewSet(viewsets.ModelViewSet):
    serializer_class = ProductBarcodeSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["product", "is_primary", "code"]
    search_fields = ["code", "product__name", "product__sku", "product__code"]
    ordering_fields = ["createdAt"]
    ordering = ["-createdAt"]

    def get_queryset(self):
        qs = ProductBarcode.objects.select_related("product").all()
        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="product__companyId_id",
            branch_id_field=None,
        )


class ProductBatchViewSet(viewsets.ModelViewSet):
    serializer_class = ProductBatchSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["product", "branch", "batch_no", "exp_date"]
    search_fields = [
        "batch_no",
        "product__name",
        "product__sku",
        "product__code",
    ]
    ordering_fields = ["exp_date", "receivedAt", "updatedAt", "qty_on_hand"]
    ordering = ["exp_date", "-receivedAt"]

    def get_queryset(self):
        qs = ProductBatch.objects.select_related("product", "branch", "supplier").all()
        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="product__companyId_id",
            branch_id_field="branch_id",
        )


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product management with company/branch scoping and inventory tracking.

    Supports anonymous access for product listing with optional filtering,
    and authenticated access with role-based permissions.
    """

    serializer_class = ProductSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)
    pagination_class = ProductPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilter
    search_fields = [
        "name",
        "sku",
        "code",
        "brand_name",
        "manufacturer",
        "category",
    ]
    ordering_fields = [
        "name",
        "price",
        "priceSale",
        "regular_price",
        "in_stock",
        "quantity",
        "totalSold",
        "totalPurchase",
        "updateAt",
        "createdAt",
    ]
    ordering = ["-updateAt"]

    def get_serializer_class(self):
        """Use ProductPostSerializer for write operations so variants are processed."""
        if self.action in ("create", "update", "partial_update"):
            return ProductPostSerializer
        return ProductSerializer

    # Temporary: allow anyone to access product search/list.
    # Later we can switch back to company/branch/role based access.
    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Product.objects.select_related(
            "unit",
            "display_unit",
            "unit_conversion_group",
            "selling_unit",
            "supplier",
            "generic_name",
            "brand",
        ).all()

        branch_id = self.request.query_params.get(
            "branch_id"
        ) or self.request.query_params.get("branchId")
        warehouse_id = self.request.query_params.get(
            "warehouse_id"
        ) or self.request.query_params.get("warehouseId")
        if branch_id:
            try:
                from products.models import ProductBranchInventory

                qs = qs.prefetch_related(
                    Prefetch(
                        "branch_inventory",
                        queryset=ProductBranchInventory.objects.filter(
                            branch_id=branch_id
                        ).only(
                            "product_id",
                            "price",
                            "priceSale",
                            "regular_price",
                            "in_stock",
                            "available",
                        ),
                        to_attr="_branch_inventory_for_request",
                    )
                )
            except Exception:
                pass

        if (
            not getattr(self.request, "user", None)
            or not self.request.user.is_authenticated
        ):
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            return qs

        qs = apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

        requested_company_id = self.request.query_params.get(
            "company_id"
        ) or self.request.query_params.get("companyId")
        if requested_company_id and not is_unrestricted_user(self.request.user):
            allowed_company_ids = get_company_ids_for_user(self.request.user)
            if (
                not allowed_company_ids
                or str(requested_company_id) not in allowed_company_ids
            ):
                raise PermissionDenied("You do not have access to this company")
            qs = qs.filter(companyId_id=requested_company_id)

        if branch_id:
            qs = qs.filter(Q(branch_id=branch_id) | Q(branch_id__isnull=True))

        if warehouse_id:
            qs = qs.filter(Q(warehouse_id=warehouse_id) | Q(warehouse_id__isnull=True))

        # Filter by location_status (warehouse/branch)
        location_status = self.request.query_params.get("location_status")
        if location_status:
            qs = qs.filter(location_status=location_status)

        # Filter by transaction_status (unsold/sold/returned/rejected)
        transaction_status = self.request.query_params.get("transaction_status")
        if transaction_status:
            qs = qs.filter(transaction_status=transaction_status)

        return qs

    # === CRUD Operations ===

    def perform_create(self, serializer):
        """Create a new product with appropriate company/branch assignment.

        If warehouse_id is provided in the request, the product is assigned to that
        warehouse (location_status=warehouse) and a PurchaseOrder with status=pending
        is automatically created.
        """
        user = getattr(self.request, "user", None)
        req_data = self.request.data if isinstance(self.request.data, dict) else {}
        warehouse_id = req_data.get("warehouse_id") or req_data.get("warehouseId")
        company_id = req_data.get("company_id") or req_data.get("companyId")

        # Resolve company
        company = None
        if user and not is_unrestricted_user(user):
            company = getattr(user, "companyId", None)
            if company is None and hasattr(user, "branchAccess"):
                company_ids = set(
                    user.branchAccess.values_list("company_id", flat=True)
                )
                if len(company_ids) == 1:
                    company_id_val = next(iter(company_ids))
                    if warehouse_id:
                        product = serializer.save(
                            companyId_id=company_id_val,
                            warehouse_id=warehouse_id,
                            location_status="warehouse",
                            transaction_status="unsold",
                        )
                    else:
                        product = serializer.save(companyId_id=company_id_val)
                    if warehouse_id:
                        self._auto_create_purchase_order(
                            product, warehouse_id, company_id or company_id_val, user
                        )
                    return

        extra_kwargs = {}
        if warehouse_id:
            extra_kwargs.update(
                warehouse_id=warehouse_id,
                location_status="warehouse",
                transaction_status="unsold",
            )
        if company:
            product = serializer.save(companyId=company, **extra_kwargs)
        elif company_id:
            product = serializer.save(companyId_id=company_id, **extra_kwargs)
        else:
            product = serializer.save(**extra_kwargs)

        if warehouse_id:
            resolved_company_id = company_id or (company.pk if company else None)
            self._auto_create_purchase_order(
                product, warehouse_id, resolved_company_id, user
            )

    def _auto_create_purchase_order(self, product, warehouse_id, company_id, user):
        """Auto-create a PurchaseOrder with status=pending when a product is added to warehouse."""
        from purchase.models import PurchaseOrder, PurchaseOrderItem
        from decimal import Decimal

        actor = (
            user.username
            if user and getattr(user, "is_authenticated", False)
            else "System"
        )

        try:
            with transaction.atomic():
                po = PurchaseOrder.objects.create(
                    warehouse_id=warehouse_id,
                    companyId_id=company_id,
                    status="pending",
                    notes=f"Auto-created when product '{product.name}' was added to warehouse",
                    created_by=actor,
                )
                variants = list(product.variants.all())
                if variants:
                    for variant in variants:
                        PurchaseOrderItem.objects.create(
                            purchase_order=po,
                            product=product,
                            variant=variant,
                            name=f"{product.name} ({variant.size or ''}{variant.color or ''})".strip(
                                " ()"
                            ),
                            quantity=max(int(variant.size_qty or 1), 1),
                            unit="pcs",
                            unit_price=Decimal(
                                str(
                                    variant.supplier_price
                                    or product.supplier_price
                                    or 0
                                )
                            ),
                            variant_size=variant.size or "",
                            variant_color=variant.color or "",
                            variant_unique_code=variant.unique_code or "",
                        )
                else:
                    PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        product=product,
                        name=product.name or "",
                        quantity=max(int(product.quantity or 1), 1),
                        unit="pcs",
                        unit_price=Decimal(str(product.supplier_price or 0)),
                    )
                po.recalc_total()
        except Exception as exc:
            # Log but don't fail the product creation
            import logging

            logging.getLogger(__name__).warning(
                "Failed to auto-create PO for product %s: %s", product.pk, exc
            )

    def perform_update(self, serializer):
        """Update a product and record stock movement audit trail."""
        prev_stock = int(
            getattr(getattr(serializer, "instance", None), "in_stock", 0) or 0
        )

        user = getattr(self.request, "user", None)
        saved = None
        if user and not is_unrestricted_user(user):
            company = getattr(user, "companyId", None)
            if company is None and hasattr(user, "branchAccess"):
                company_ids = set(
                    user.branchAccess.values_list("company_id", flat=True)
                )
                if len(company_ids) == 1:
                    saved = serializer.save(companyId_id=next(iter(company_ids)))
                else:
                    saved = serializer.save(companyId=company)
            else:
                saved = serializer.save(companyId=company)
        else:
            saved = serializer.save()

        # Record an audit trail when stock changes via normal updates (PATCH/PUT).
        # This is important because some clients update `in_stock` directly instead
        # of calling the dedicated `add_stock` / `reduce_stock` actions.
        new_stock = int(getattr(saved, "in_stock", 0) or 0)
        if prev_stock != new_stock:
            delta = new_stock - prev_stock
            ProductStockMovement.objects.create(
                product=saved,
                movement_type="adjustment",
                quantity=Decimal(abs(delta)),
                previous_stock=Decimal(prev_stock),
                new_stock=Decimal(new_stock),
                reason="Stock updated",
                notes=f"{self.request.method} {self.request.path}",
                created_by=(
                    user.username
                    if user and getattr(user, "is_authenticated", False)
                    else "System"
                ),
            )

    # === Custom Update Methods ===

    def update(self, request, *args, **kwargs):
        branch_id = request.query_params.get("branch_id") or request.query_params.get(
            "branchId"
        )
        if branch_id:
            product = self.get_object()
            branch = resolve_branch_from_request(request, product=product)
            if not branch:
                return Response(
                    {"detail": "Invalid branch_id"}, status=status.HTTP_400_BAD_REQUEST
                )

            branch_fields = {
                "in_stock",
                "available",
                "price",
                "priceSale",
                "regular_price",
            }
            branch_data = {
                k: request.data.get(k) for k in branch_fields if k in request.data
            }

            catalog_allowed = {
                "name",
                "sku",
                "brand_name",
                "manufacturer",
                "code",
                "category",
                "description",
                "model",
                "coverUrl",
                "image",
                "size",
                "subDescription",
                "unit",
                "secondary_unit",
                "unit_conversion_factor",
                "unit_conversion_group",
                "display_unit",
                "selling_unit",
                "selling_unit_conversion_factor",
                "price",
                "priceSale",
                "regular_price",
                "supplier_price",
                "generic_name",
                "exp_date",
                "mfg_date",
                "inventoryType",
                "quantity",
                "low_stock_threshold",
                "variants",
            }
            catalog_data = {
                k: v for k, v in request.data.items() if k in catalog_allowed
            }

            if catalog_data:
                serializer = self.get_serializer(
                    product, data=catalog_data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                product = serializer.save()

            if branch_data:
                update_branch_fields(
                    product, branch, fields=branch_data, updated_by=request.user
                )

            ser = self.get_serializer(product)
            return Response(ser.data)

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        branch_id = request.query_params.get("branch_id") or request.query_params.get(
            "branchId"
        )
        if branch_id:
            product = self.get_object()
            branch = resolve_branch_from_request(request, product=product)
            if not branch:
                return Response(
                    {"detail": "Invalid branch_id"}, status=status.HTTP_400_BAD_REQUEST
                )

            branch_fields = {
                "in_stock",
                "available",
                "price",
                "priceSale",
                "regular_price",
            }
            branch_data = {
                k: request.data.get(k) for k in branch_fields if k in request.data
            }

            catalog_allowed = {
                "name",
                "sku",
                "brand_name",
                "manufacturer",
                "code",
                "category",
                "description",
                "model",
                "coverUrl",
                "image",
                "size",
                "subDescription",
                "unit",
                "secondary_unit",
                "unit_conversion_factor",
                "unit_conversion_group",
                "display_unit",
                "selling_unit",
                "selling_unit_conversion_factor",
                "price",
                "priceSale",
                "regular_price",
                "supplier_price",
                "generic_name",
                "exp_date",
                "mfg_date",
                "inventoryType",
                "quantity",
                "low_stock_threshold",
                "variants",
            }
            catalog_data = {
                k: v for k, v in request.data.items() if k in catalog_allowed
            }

            if catalog_data:
                serializer = self.get_serializer(
                    product, data=catalog_data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                product = serializer.save()

            if branch_data:
                update_branch_fields(
                    product, branch, fields=branch_data, updated_by=request.user
                )

            ser = self.get_serializer(product)
            return Response(ser.data)

        return super().partial_update(request, *args, **kwargs)

    # === Stock Management Actions ===

    @action(detail=True, methods=["post"])
    def add_stock(self, request, pk=None):
        """Increase Product stock and record a movement."""
        product = self.get_object()
        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qty: Decimal = serializer.validated_data["quantity"]
        if qty != qty.to_integral_value():
            return Response(
                {"detail": "Quantity must be a whole number for products."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qty_int = int(qty)

        branch = resolve_branch_from_request(request, product=product)
        if branch:
            adjust_branch_stock(
                product,
                branch,
                delta=qty_int,
                reason=serializer.validated_data.get("reason", "Stock addition"),
                notes=serializer.validated_data.get("notes", ""),
                updated_by=request.user,
            )
            # Also update StockSummary for this branch
            try:
                stock_summary, _ = StockSummary.objects.get_or_create(
                    product=product,
                    variant=None,
                    branch=branch,
                    warehouse=None,
                    location="in_branch",
                    defaults={"company": product.companyId, "quantity": 0},
                )
                stock_summary.quantity += qty_int
                stock_summary.save(update_fields=["quantity"])
            except Exception as e:
                print(f"Error updating StockSummary for branch: {e}")
        else:
            prev = int(product.in_stock or 0)
            new = prev + qty_int
            product.in_stock = new
            product.quantity = new
            product.available = new
            product.save(
                update_fields=[
                    "in_stock",
                    "in_stock_secondary",
                    "quantity",
                    "available",
                    "updateAt",
                ]
            )
            # Also update StockSummary for warehouse (when no branch specified)
            try:
                stock_summary, _ = StockSummary.objects.get_or_create(
                    product=product,
                    variant=None,
                    warehouse=product.warehouse,
                    branch=None,
                    location="in_warehouse",
                    defaults={"company": product.companyId, "quantity": 0},
                )
                stock_summary.quantity += qty_int
                stock_summary.save(update_fields=["quantity"])
            except Exception as e:
                print(f"Error updating StockSummary for warehouse: {e}")

            ProductStockMovement.objects.create(
                product=product,
                movement_type="in",
                quantity=qty,
                previous_stock=Decimal(prev),
                new_stock=Decimal(new),
                reason=serializer.validated_data.get("reason", "Stock addition"),
                notes=serializer.validated_data.get("notes", ""),
                reference_number=serializer.validated_data.get("reference_number", ""),
                created_by=(
                    request.user.username
                    if request.user and request.user.is_authenticated
                    else "System"
                ),
            )

        return Response(ProductSerializer(product, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def reduce_stock(self, request, pk=None):
        """Decrease Product stock and record a movement."""
        product = self.get_object()
        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qty: Decimal = serializer.validated_data["quantity"]
        if qty != qty.to_integral_value():
            return Response(
                {"detail": "Quantity must be a whole number for products."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qty_int = int(qty)

        branch = resolve_branch_from_request(request, product=product)
        if branch:
            # Keep legacy behavior: don't reduce below 0
            from products.branch_inventory import get_effective_numbers

            current = get_effective_numbers(product, branch).in_stock
            actual = min(int(current), int(qty_int))
            adjust_branch_stock(
                product,
                branch,
                delta=-actual,
                reason=serializer.validated_data.get("reason", "Stock reduction"),
                notes=serializer.validated_data.get("notes", ""),
                updated_by=request.user,
            )
            # Also update StockSummary for this branch
            try:
                stock_summary, _ = StockSummary.objects.get_or_create(
                    product=product,
                    variant=None,
                    branch=branch,
                    warehouse=None,
                    location="in_branch",
                    defaults={"company": product.companyId, "quantity": 0},
                )
                stock_summary.quantity = max(0, stock_summary.quantity - actual)
                stock_summary.save(update_fields=["quantity"])
            except Exception as e:
                print(f"Error updating StockSummary for branch: {e}")
        else:
            prev = int(product.in_stock or 0)
            actual = min(prev, qty_int)
            new = prev - actual
            product.in_stock = new
            product.quantity = new
            product.available = new
            product.save(
                update_fields=[
                    "in_stock",
                    "in_stock_secondary",
                    "quantity",
                    "available",
                    "updateAt",
                ]
            )
            # Also update StockSummary for warehouse (when no branch specified)
            try:
                stock_summary, _ = StockSummary.objects.get_or_create(
                    product=product,
                    variant=None,
                    warehouse=product.warehouse,
                    branch=None,
                    location="in_warehouse",
                    defaults={"company": product.companyId, "quantity": 0},
                )
                stock_summary.quantity = max(0, stock_summary.quantity - actual)
                stock_summary.save(update_fields=["quantity"])
            except Exception as e:
                print(f"Error updating StockSummary for warehouse: {e}")

            ProductStockMovement.objects.create(
                product=product,
                movement_type="out",
                quantity=Decimal(actual),
                previous_stock=Decimal(prev),
                new_stock=Decimal(new),
                reason=serializer.validated_data.get("reason", "Stock reduction"),
                notes=serializer.validated_data.get("notes", ""),
                reference_number=serializer.validated_data.get("reference_number", ""),
                created_by=(
                    request.user.username
                    if request.user and request.user.is_authenticated
                    else "System"
                ),
            )

        return Response(ProductSerializer(product, context={"request": request}).data)

    # === Other Actions ===

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        """Return stock movement history for a Product."""
        product = self.get_object()
        qs = ProductStockMovement.objects.filter(product=product).order_by(
            "-created_at"
        )
        ser = ProductStockMovementSerializer(qs, many=True)
        return Response(ser.data)


class ProductPostSet(viewsets.ModelViewSet):
    serializer_class = ProductPostSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)

    def _resolve_company_for_user(self):
        user = getattr(self.request, "user", None)
        if not user or is_unrestricted_user(user):
            return None

        company = getattr(user, "companyId", None)
        if company is not None:
            return company

        if hasattr(user, "branchAccess"):
            company_ids = set(user.branchAccess.values_list("company_id", flat=True))
            if len(company_ids) == 1:
                from company.models import Company

                return Company.objects.filter(id=next(iter(company_ids))).first()

        return None

    def _resolve_branch_for_user(self):
        user = getattr(self.request, "user", None)
        # Only anonymous requests should return early.
        if not user:
            return None

        branch_id = self.request.query_params.get(
            "branch_id"
        ) or self.request.query_params.get("branchId")
        if not branch_id:
            return None

        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if allowed_branch_ids is not None and str(branch_id) not in allowed_branch_ids:
            raise PermissionDenied("You do not have access to this branch")

        # If the user has explicit branchAccess, use it.
        if hasattr(user, "branchAccess"):
            branch = user.branchAccess.filter(id=branch_id).first()
            if branch:
                return branch

        # Fallback: allow resolving branch directly (useful for unrestricted users)
        try:
            from company.models import Branch as CompanyBranch

            branch = CompanyBranch.objects.filter(id=branch_id).first()
            return branch
        except Exception:
            return None

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        # if not user or is_unrestricted_user(user):
        #     serializer.save()
        #     return

        if not user:
            serializer.save()
            return

        company = self._resolve_company_for_user()
        if not company:
            # Fall back to company IDs derived from branch access
            company_ids = get_company_ids_for_user(user)
            if len(company_ids) == 1:
                serializer.save(
                    companyId_id=next(iter(company_ids)),
                    branch=self._resolve_branch_for_user(),
                )
                return
            raise PermissionDenied("User is not associated with a company")
        serializer.save(companyId=company, branch=self._resolve_branch_for_user())

    def perform_update(self, serializer):
        user = getattr(self.request, "user", None)
        logger.debug(
            "ProductViewSet.perform_update start id=%s data=%s",
            getattr(getattr(serializer, "instance", None), "pk", None),
            {
                key: self.request.data.get(key)
                for key in [
                    "unit",
                    "display_unit",
                    "unit_conversion_group",
                    "selling_unit",
                    "selling_unit_conversion_factor",
                    "in_stock",
                    "quantity",
                    "available",
                ]
            },
        )
        if not user or is_unrestricted_user(user):
            product = serializer.save()
            logger.debug(
                "ProductViewSet.perform_update saved id=%s display_unit=%s unit_conversion_group=%s selling_unit=%s selling_unit_conversion_factor=%s in_stock=%s quantity=%s available=%s",
                getattr(product, "pk", None),
                getattr(product, "display_unit_id", None),
                getattr(product, "unit_conversion_group_id", None),
                getattr(product, "selling_unit_id", None),
                getattr(product, "selling_unit_conversion_factor", None),
                getattr(product, "in_stock", None),
                getattr(product, "quantity", None),
                getattr(product, "available", None),
            )
            return

        instance = getattr(serializer, "instance", None)
        company = self._resolve_company_for_user() or getattr(
            instance, "companyId", None
        )

        save_kwargs = {"companyId": company}
        branch = self._resolve_branch_for_user()
        if branch is not None:
            save_kwargs["branch"] = branch

        product = serializer.save(**save_kwargs)
        logger.debug(
            "ProductViewSet.perform_update saved id=%s display_unit=%s unit_conversion_group=%s selling_unit=%s selling_unit_conversion_factor=%s in_stock=%s quantity=%s available=%s",
            getattr(product, "pk", None),
            getattr(product, "display_unit_id", None),
            getattr(product, "unit_conversion_group_id", None),
            getattr(product, "selling_unit_id", None),
            getattr(product, "selling_unit_conversion_factor", None),
            getattr(product, "in_stock", None),
            getattr(product, "quantity", None),
            getattr(product, "available", None),
        )

    def get_queryset(self):
        qs = Product.objects.select_related(
            "unit",
            "unit_conversion_group",
            "display_unit",
            "selling_unit",
            "secondary_unit",
        ).all()
        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

    @action(detail=True, methods=["post"])
    def add_stock(self, request, pk=None):
        """Increase Product stock and record a movement."""
        product = self.get_object()
        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qty: Decimal = serializer.validated_data["quantity"]
        if qty != qty.to_integral_value():
            return Response(
                {"detail": "Quantity must be a whole number for products."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qty_int = int(qty)

        prev = int(product.in_stock or 0)
        new = prev + qty_int

        product.in_stock = new
        product.quantity = new
        product.available = new
        product.save(
            update_fields=[
                "in_stock",
                "in_stock_secondary",
                "quantity",
                "available",
                "updateAt",
            ]
        )

        ProductStockMovement.objects.create(
            product=product,
            movement_type="in",
            quantity=qty,
            previous_stock=Decimal(prev),
            new_stock=Decimal(new),
            reason=serializer.validated_data.get("reason", "Stock addition"),
            notes=serializer.validated_data.get("notes", ""),
            reference_number=serializer.validated_data.get("reference_number", ""),
            created_by=(
                request.user.username
                if request.user and request.user.is_authenticated
                else "System"
            ),
        )

        return Response(ProductSerializer(product).data)

    @action(detail=True, methods=["post"])
    def reduce_stock(self, request, pk=None):
        """Decrease Product stock and record a movement."""
        product = self.get_object()
        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qty: Decimal = serializer.validated_data["quantity"]
        if qty != qty.to_integral_value():
            return Response(
                {"detail": "Quantity must be a whole number for products."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qty_int = int(qty)

        prev = int(product.in_stock or 0)
        actual = min(prev, qty_int)
        new = prev - actual

        product.in_stock = new
        product.quantity = new
        product.available = new
        product.save(
            update_fields=[
                "in_stock",
                "in_stock_secondary",
                "quantity",
                "available",
                "updateAt",
            ]
        )

        ProductStockMovement.objects.create(
            product=product,
            movement_type="out",
            quantity=Decimal(actual),
            previous_stock=Decimal(prev),
            new_stock=Decimal(new),
            reason=serializer.validated_data.get("reason", "Stock reduction"),
            notes=serializer.validated_data.get("notes", ""),
            reference_number=serializer.validated_data.get("reference_number", ""),
            created_by=(
                request.user.username
                if request.user and request.user.is_authenticated
                else "System"
            ),
        )

        return Response(ProductSerializer(product).data)

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        """Return stock movement history for a Product."""
        product = self.get_object()
        qs = ProductStockMovement.objects.filter(product=product).order_by(
            "-created_at"
        )
        ser = ProductStockMovementSerializer(qs, many=True)
        return Response(ser.data)


class ProductSerialItemViewSet(viewsets.ModelViewSet):
    """
    Item-level barcode/serial tracking for physical units in warehouse or branch.

    Standard CRUD + three custom actions:
      GET  serial-items/lookup/?code=<serial_code>  — identify a unit by code
      POST serial-items/<id>/scan/                  — record a scan + update status
      POST serial-items/generate/                   — bulk-create N serial items
    """

    serializer_class = ProductSerialItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ProductSerialItem.objects.select_related(
            "product", "variant", "warehouse", "branch"
        )
        p = self.request.query_params
        if p.get("warehouse_id"):
            qs = qs.filter(warehouse_id=p["warehouse_id"])
        if p.get("variant_id") or p.get("variant"):
            qs = qs.filter(variant_id=p.get("variant_id") or p.get("variant"))
        if p.get("product_id") or p.get("product"):
            qs = qs.filter(product_id=p.get("product_id") or p.get("product"))
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("branch_id") or p.get("branch"):
            qs = qs.filter(branch_id=p.get("branch_id") or p.get("branch"))
        if p.get("barcode") or p.get("serial_code"):
            qs = qs.filter(serial_code=p.get("barcode") or p.get("serial_code"))
        if p.get("company"):
            qs = qs.filter(product__companyId_id=p["company"])
        return qs

    @action(detail=False, methods=["get"], url_path="lookup")
    def lookup(self, request):
        """GET ?code=<serial_code> — returns the serial item if found, 404 otherwise."""
        code = request.query_params.get("code", "").strip()
        if not code:
            return Response(
                {"detail": "code query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        item = (
            ProductSerialItem.objects.select_related(
                "product", "variant__product", "warehouse", "branch"
            )
            .filter(serial_code=code)
            .first()
        )
        if not item:
            return Response(
                {"found": False, "code": code},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = self.get_serializer(item).data
        data["found"] = True
        return Response(data)

    @action(detail=True, methods=["post"], url_path="scan")
    def scan(self, request, pk=None):
        """Record a scan timestamp and optionally update status, condition, notes."""
        from django.utils.timezone import now as tz_now

        item = self.get_object()
        item.last_scanned_at = tz_now()
        update_fields = ["last_scanned_at", "updated_at"]
        if "status" in request.data:
            item.status = request.data["status"]
            update_fields.append("status")
        if "condition" in request.data:
            item.condition = request.data["condition"]
            update_fields.append("condition")
        if "notes" in request.data:
            item.notes = request.data["notes"]
            update_fields.append("notes")
        item.save(update_fields=update_fields)
        return Response(self.get_serializer(item).data)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """
        Bulk-create N serial items for a given variant or product.

        Body: { variant_id, product_id, quantity, warehouse_id (optional) }
        """
        variant_id = request.data.get("variant_id")
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 0))
        if quantity <= 0:
            return Response(
                {"detail": "quantity must be > 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not variant_id and not product_id:
            return Response(
                {"detail": "variant_id or product_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        warehouse_id = request.data.get("warehouse_id")
        variant = None
        product = None
        if variant_id:
            try:
                variant = ProductVariant.objects.select_related("product").get(
                    id=variant_id
                )
                product = variant.product
            except ProductVariant.DoesNotExist:
                return Response(
                    {"detail": "Variant not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {"detail": "Product not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        # Resolve warehouse_id fallback from product
        if not warehouse_id and product:
            warehouse_id = getattr(product, "warehouse_id", None)
        created = []
        for _ in range(quantity):
            item = ProductSerialItem(
                product=product,
                variant=variant,
                warehouse_id=warehouse_id,
            )
            item.save()
            created.append(item)
        return Response(
            self.get_serializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class PicturePostSet(viewsets.ModelViewSet):
    serializer_class = PictureSerializer

    def get_queryset(self):
        return Image.objects.all()


class NewLabelSet(viewsets.ModelViewSet):
    serializer_class = NewLavelSerializer

    def get_queryset(self):
        return NewLabel.objects.all()


class SaleLabelSet(viewsets.ModelViewSet):
    serializer_class = SaleLavelSerializer

    def get_queryset(self):
        return SaleLabel.objects.all()


class PosProductIndexPagination(PageNumberPagination):
    """Pagination for lightweight product index syncing to Dexie/IndexedDB.

    Optimized for fast bulk sync of 20k+ product catalogs.
    """

    page_size = 500  # Increased from 200 for faster sync
    page_size_query_param = "page_size"
    max_page_size = 5000  # Increased from 2000 to allow larger bulk syncs


class PosProductIndexView(APIView):
    """A lightweight product index endpoint for POS/Dexie sync.

    Returns only the fields needed for barcode lookup + cart pricing.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Lightweight query: only fetch fields needed for POS index (barcode, pricing, inventory)
        # This reduces database query time and network payload by 40-60%
        qs = (
            Product.objects.select_related("unit", "supplier")
            .only(
                "id",
                "name",
                "category",
                "code",
                "sku",
                "price",
                "priceSale",
                "regular_price",
                "in_stock",
                "quantity",
                "available",
                "image",
                "coverUrl",
                "updated_at",
            )
            .defer(
                "description", "ingredients", "allergens", "notes", "short_description"
            )
            .all()
        )

        qs = apply_company_branch_scope(
            request=request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

        # Optional explicit company scoping (for users who can switch company in UI).
        requested_company_id = request.query_params.get(
            "company_id"
        ) or request.query_params.get("companyId")
        if requested_company_id and not is_unrestricted_user(request.user):
            allowed_company_ids = get_company_ids_for_user(request.user)
            if (
                not allowed_company_ids
                or str(requested_company_id) not in allowed_company_ids
            ):
                raise PermissionDenied("You do not have access to this company")
            qs = qs.filter(companyId_id=requested_company_id)

        updated_since = request.query_params.get(
            "updated_since"
        ) or request.query_params.get("updatedSince")
        if updated_since:
            dt = parse_datetime(updated_since)
            if dt is None:
                d = parse_date(updated_since)
                if d is not None:
                    dt = datetime.combine(d, time.min)

            if dt is not None:
                if is_naive(dt):
                    dt = make_aware(dt, get_default_timezone())
                qs = qs.filter(updated_at__gt=dt)

        # Stable ordering for pagination (critical for consistent sync across pages)
        qs = qs.order_by("-updated_at", "id")

        payload = qs.values(
            "id",
            "name",
            "category",
            "code",
            "sku",
            "price",
            "priceSale",
            "regular_price",
            "taxes",
            "in_stock",
            "quantity",
            "available",
            "image",
            "coverUrl",
            "updated_at",
        )

        paginator = PosProductIndexPagination()
        page = paginator.paginate_queryset(payload, request)
        return paginator.get_paginated_response(page)


class POSCatalogView(APIView):
    """Branch-scoped POS catalog derived from StockSummary.

    GET /api/pos/catalog/?branch_id=<uuid>[&category=<name>][&search=<q>][&page=<n>][&page_size=<n>]

    Returns only items whose ``quantity > 0`` and ``location='in_branch'``.
    Each result row is ready to be loaded directly into the POS cart.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        branch_id = request.query_params.get("branch_id") or request.query_params.get(
            "branchId"
        )
        if not branch_id:
            return Response(
                {"success": False, "error": "branch_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Access-control: non-privileged users may only see their own branches.
        if not is_unrestricted_user(request.user):
            allowed_branch_ids = get_allowed_branch_ids_for_user(request.user)
            if allowed_branch_ids is not None and str(branch_id) not in {
                str(b) for b in allowed_branch_ids
            }:
                return Response(
                    {"success": False, "error": "Access denied"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        qs = (
            StockSummary.objects.filter(
                branch_id=branch_id,
                location="in_branch",
            )
            .select_related(
                "product",
                "product__display_unit",
                "product__unit",
                "product__unit_conversion_group",
                "variant",
            )
            .order_by("product__name", "variant__size")
        )

        category = request.query_params.get("category")
        if category:
            qs = qs.filter(product__category__iexact=category)

        q = request.query_params.get("search") or request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(product__name__icontains=q)
                | Q(product__code__icontains=q)
                | Q(variant__size__icontains=q)
                | Q(variant__size_code__icontains=q)
            )

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(200, max(1, int(request.query_params.get("page_size", 80))))
        except (ValueError, TypeError):
            page = 1
            page_size = 80

        total = qs.count()
        offset = (page - 1) * page_size
        items = qs[offset : offset + page_size]
        has_next = (offset + page_size) < total

        serializer = StockSummaryPOSSerializer(items, many=True)
        return Response(
            {
                "success": True,
                "data": {
                    "count": total,
                    "next": has_next,
                    "previous": page > 1,
                    "results": serializer.data,
                },
            }
        )


class StockTransferViewSet(viewsets.ModelViewSet):
    """
    CRUD + complete/cancel actions for StockTransfer.

    GET  /api/stock-transfers/?company=<id>   — list
    POST /api/stock-transfers/               — create (with nested items)
    POST /api/stock-transfers/<id>/complete/ — execute transfer
    POST /api/stock-transfers/<id>/cancel/   — cancel transfer
    """

    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return StockTransferCreateSerializer
        return StockTransferSerializer

    def get_queryset(self):
        qs = StockTransfer.objects.prefetch_related(
            "items__serial_item",
            "items__product",
            "items__variant",
        ).select_related(
            "company",
            "source_warehouse",
            "source_branch",
            "destination_warehouse",
            "destination_branch",
        )
        p = self.request.query_params
        if p.get("company"):
            qs = qs.filter(company_id=p["company"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("transfer_type"):
            qs = qs.filter(transfer_type=p["transfer_type"])
        return qs.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = StockTransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = serializer.save()
        return Response(
            StockTransferSerializer(transfer).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Execute the transfer: update serial items + StockSummary."""
        transfer = self.get_object()
        try:
            transfer.complete_transfer()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockTransferSerializer(transfer).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancel a draft or in-transit transfer."""
        transfer = self.get_object()
        if transfer.status not in ("draft", "in_transit"):
            return Response(
                {
                    "detail": f"Cannot cancel a transfer with status '{transfer.status}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        transfer.status = "cancelled"
        transfer.save(update_fields=["status", "updated_at"])
        return Response(StockTransferSerializer(transfer).data)
