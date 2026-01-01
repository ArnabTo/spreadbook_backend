from rest_framework.decorators import permission_classes, action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, viewsets, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.timezone import get_default_timezone, is_naive, make_aware
from datetime import datetime, time

from .models.category_model import Category
from .models.product_model import Product, Image, NewLabel, SaleLabel, Size, Color
from .pagination import ProductPagination
from .serializers import (
    ProductSerializer,
    ProductPostSerializer,
    PictureSerializer,
    NewLavelSerializer,
    SaleLavelSerializer,
)
from .serializers import CategorySerializer, ColorSerializer, SizeSerializer


from rest_framework import generics
from django.shortcuts import render

from common.drf_scoping import (
    apply_company_branch_scope,
    is_unrestricted_user,
    get_company_ids_for_user,
)
from rest_framework.exceptions import PermissionDenied

from decimal import Decimal

from .models.inventory_model import ProductStockMovement
from .serializers import AddStockSerializer, ProductStockMovementSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = CategorySerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return Category.objects.all()


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


class ProductViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # http_method_names= ['get']
    pagination_class = ProductPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "category",
        "status",
        "inventoryType",
        "is_publish",
        "supplier",
        "unit",
    ]
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

    def get_queryset(self):
        qs = Product.objects.select_related("unit", "supplier").all()
        qs = apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

        # Optional explicit company scoping (for users who can switch company in UI).
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

        return qs

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        if user and not is_unrestricted_user(user):
            company = getattr(user, "companyId", None)
            if company is None and hasattr(user, "branchAccess"):
                company_ids = set(
                    user.branchAccess.values_list("company_id", flat=True)
                )
                if len(company_ids) == 1:
                    serializer.save(companyId_id=next(iter(company_ids)))
                    return

            serializer.save(companyId=company)
            return
        serializer.save()

    def perform_update(self, serializer):
        user = getattr(self.request, "user", None)
        if user and not is_unrestricted_user(user):
            company = getattr(user, "companyId", None)
            if company is None and hasattr(user, "branchAccess"):
                company_ids = set(
                    user.branchAccess.values_list("company_id", flat=True)
                )
                if len(company_ids) == 1:
                    serializer.save(companyId_id=next(iter(company_ids)))
                    return

            serializer.save(companyId=company)
            return
        serializer.save()


class ProductPostSet(viewsets.ModelViewSet):
    serializer_class = ProductPostSerializer

    def get_queryset(self):
        qs = Product.objects.all()
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
        product.save(update_fields=["in_stock", "quantity", "available", "updateAt"])

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
        product.save(update_fields=["in_stock", "quantity", "available", "updateAt"])

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
    page_size = 200
    page_size_query_param = "page_size"
    max_page_size = 2000


class PosProductIndexView(APIView):
    """A lightweight product index endpoint for POS/Dexie sync.

    Returns only the fields needed for barcode lookup + cart pricing.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Product.objects.all()
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

        # Stable ordering for pagination.
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
