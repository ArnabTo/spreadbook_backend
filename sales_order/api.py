from __future__ import annotations

import json
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authenticator.models import User as UserModel
from common.drf_scoping import (
    apply_company_branch_scope,
    get_company_ids_for_user,
    is_unrestricted_user,
)
from customers.models import Customer
from financial_years.models import FinancialYear
from prefixes.models import Prefix
from products.models import Product, Unit
from sales_quotation.models import Currency
from sales_quotation.serializers import CurrencySerializer

from .models import SalesOrder, SalesOrderItem
from .serializers import (
    SalesOrderDetailSerializer,
    SalesOrderItemSerializer,
    SalesOrderListSerializer,
    SalesOrderWriteSerializer,
)


def _generate_bill_number(company, financial_year=None) -> str:
    """Generate the next sales order number atomically using the Prefix system.

    Falls back to SO-<n> within the company if no Prefix record exists.
    """

    if not company:
        return ""

    qs = Prefix.objects.filter(
        company=company, type="sales_order", applicable=True
    )
    if financial_year is not None:
        qs = qs.filter(financial_year=financial_year)
    else:
        qs = qs.filter(financial_year__isnull=True)

    with transaction.atomic():
        prefix_obj = qs.select_for_update().order_by("id").first()
        if prefix_obj is None:
            last_qs = (
                SalesOrder.objects.filter(companyId=company)
                .order_by("-created_at")
                .values_list("bill_number", flat=True)
            )
            last = next(iter(last_qs), None)
            next_index = 100
            if last:
                try:
                    tail = str(last).split("-")[-1]
                    next_index = int("".join(ch for ch in tail if ch.isdigit())) + 1
                except (ValueError, IndexError):
                    next_index = 100
            return f"SO-{next_index}"

        Prefix.objects.filter(pk=prefix_obj.pk).update(
            current_index=F("current_index") + 1
        )
        prefix_obj.refresh_from_db(fields=["current_index"])
        new_index = prefix_obj.current_index
        sep = prefix_obj.separator or "-"
        try:
            width = max(3, len(str(prefix_obj.start_index or 0)))
        except Exception:
            width = 3
        return f"{prefix_obj.prefix}{sep}{new_index:0{width}d}"


class SalesOrderPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        from rest_framework.response import Response as DRFResponse

        return DRFResponse(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


class SalesOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    pagination_class = SalesOrderPageNumberPagination

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SalesOrderWriteSerializer
        if self.action == "retrieve":
            return SalesOrderDetailSerializer
        return SalesOrderListSerializer

    def get_queryset(self):
        qs = (
            SalesOrder.objects.select_related(
                "customer",
                "currency",
                "sales_person",
            )
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=SalesOrderItem.objects.select_related(
                        "product", "unit"
                    ),
                )
            )
            .all()
        )
        qs = apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )
        params = self.request.query_params
        bill_number = params.get("bill_number")
        if bill_number:
            qs = qs.filter(bill_number__icontains=bill_number)
        customer_id = params.get("customer")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        date_from = params.get("date_from")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        date_to = params.get("date_to")
        if date_to:
            qs = qs.filter(date__lte=date_to)
        po_ref = params.get("po_ref")
        if po_ref:
            qs = qs.filter(po_ref__icontains=po_ref)
        salesperson = params.get("sales_person")
        if salesperson:
            qs = qs.filter(sales_person_id=salesperson)
        return qs.order_by("-date", "-created_at")

    # ---- write helpers ----
    def _resolve_company(self, user, requested_company_id=None):
        if is_unrestricted_user(user):
            if requested_company_id:
                from company.models import Company

                return Company.objects.filter(id=requested_company_id).first()
            return getattr(user, "companyId", None)
        ids = list(get_company_ids_for_user(user))
        if not ids:
            return None
        from company.models import Company

        if requested_company_id and str(requested_company_id) in [str(i) for i in ids]:
            return Company.objects.filter(id=requested_company_id).first()
        return Company.objects.filter(id__in=ids).first()

    def _resolve_branch(self, user, requested_branch_id=None):
        if not requested_branch_id:
            return None
        from company.models import Branch

        if is_unrestricted_user(user):
            return Branch.objects.filter(id=requested_branch_id).first()
        allowed = user.branchAccess.values_list("id", flat=True)
        if int(requested_branch_id) in [int(b) for b in allowed]:
            return Branch.objects.filter(id=requested_branch_id).first()
        raise PermissionDenied("You do not have access to this branch")

    def _build_items(self, items_data):
        objects = []
        for idx, raw in enumerate(items_data or []):
            product_id = raw.get("product")
            unit_id = raw.get("unit")
            product = (
                Product.objects.filter(id=product_id).first()
                if product_id
                else None
            )
            unit = (
                Unit.objects.filter(id=unit_id).first()
                if unit_id
                else None
            )
            try:
                qty = Decimal(str(raw.get("qty") or 0))
            except Exception:
                qty = Decimal("0")
            try:
                rate = Decimal(str(raw.get("rate") or 0))
            except Exception:
                rate = Decimal("0")
            try:
                discount_amount = Decimal(str(raw.get("discount_amount") or 0))
            except Exception:
                discount_amount = Decimal("0")
            try:
                tax_percent = Decimal(str(raw.get("tax_percent") or 0))
            except Exception:
                tax_percent = Decimal("0")
            product_total = qty * rate
            amount = product_total - discount_amount
            tax_amount = (amount * tax_percent) / Decimal("100")
            total = amount + tax_amount
            objects.append(
                SalesOrderItem(
                    product=product,
                    unit=unit,
                    qty=qty,
                    rate=rate,
                    discount_amount=discount_amount,
                    product_total=product_total,
                    amount=amount,
                    tax_percent=tax_percent,
                    tax_amount=tax_amount,
                    total=total,
                    si_no=int(raw.get("si_no") or idx + 1),
                )
            )
        return objects

    def _recalc_totals(self, order: SalesOrder, items_data):
        items = self._build_items(items_data)
        total = sum((i.amount for i in items), Decimal("0"))
        tax_total = sum((i.tax_amount for i in items), Decimal("0"))
        product_discount_total = sum((i.discount_amount for i in items), Decimal("0"))
        try:
            cash_discount_total = Decimal(str(self.request.data.get("cash_discount_total") or 0))
        except Exception:
            cash_discount_total = Decimal("0")
        grand_total = total + tax_total - product_discount_total - cash_discount_total
        order.total = total
        order.tax_total = tax_total
        order.product_discount_total = product_discount_total
        order.cash_discount_total = cash_discount_total
        order.grand_total = grand_total
        return items

    # ---- create / update ----
    def _get_products_payload(self, request):
        products = None
        try:
            products = request.data.get("products")
        except Exception:
            products = None
        if isinstance(products, str):
            try:
                parsed = json.loads(products)
            except (ValueError, TypeError):
                parsed = None
            if isinstance(parsed, list):
                return parsed
        if isinstance(products, list):
            return products
        return []

    def _build_request_data_for_serializer(self, request, products_list):
        data = {}
        try:
            items = request.data.items()
        except Exception:
            items = []
        for k, v in items:
            if k == "products":
                continue
            data[k] = v
        data["products"] = products_list
        return data

    def create(self, request, *args, **kwargs):
        products_list = self._get_products_payload(request)
        payload = self._build_request_data_for_serializer(request, products_list)
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        items_data = validated.pop("products", []) or []

        user = request.user
        with transaction.atomic():
            company = self._resolve_company(user)
            if not company:
                raise PermissionDenied("No company context available for current user")
            branch = self._resolve_branch(
                user, request.data.get("branch") or validated.get("branch")
            )

            fy = validated.get("financial_year")
            if fy is None:
                fy = (
                    FinancialYear.objects.filter(
                        company=company, closed=False
                    )
                    .order_by("-from_date")
                    .first()
                )

            order = SalesOrder(companyId=company, branch=branch, user=user)
            for field, value in validated.items():
                if field in ("attachment",):
                    continue
                setattr(order, field, value)
            attachment = request.FILES.get("attachment")
            if attachment is not None:
                order.attachment = attachment
            order.bill_number = _generate_bill_number(company, fy)
            order.financial_year = fy
            item_objs = self._recalc_totals(order, items_data)
            order.save()

            for item in item_objs:
                item.order = order
            SalesOrderItem.objects.bulk_create(item_objs)

        out = SalesOrderDetailSerializer(order).data
        return Response(out, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        products_list = self._get_products_payload(request)
        payload = self._build_request_data_for_serializer(request, products_list)
        serializer = self.get_serializer(instance, data=payload, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        items_data = validated.pop("products", None)

        with transaction.atomic():
            for field, value in validated.items():
                if field in ("attachment",):
                    continue
                setattr(instance, field, value)
            attachment = request.FILES.get("attachment")
            if attachment is not None:
                instance.attachment = attachment
            if items_data is not None:
                self._recalc_totals(instance, items_data)
            instance.save()

            if items_data is not None:
                instance.items.all().delete()
                new_items = self._build_items(items_data)
                for it in new_items:
                    it.order = instance
                SalesOrderItem.objects.bulk_create(new_items)

        out = SalesOrderDetailSerializer(instance).data
        return Response(out)

    def perform_destroy(self, instance):
        user = self.request.user
        if not is_unrestricted_user(user):
            ids = get_company_ids_for_user(user)
            if not ids or str(instance.companyId_id) not in [str(i) for i in ids]:
                raise PermissionDenied("You cannot delete this order")
        instance.delete()

    # ---- actions ----
    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        """Return dropdown options scoped to current company."""

        def apply_scope(qs):
            return apply_company_branch_scope(
                request=request,
                queryset=qs,
                company_id_field="companyId_id",
                branch_id_field=None,
            )

        customers = apply_scope(Customer.objects.all()).order_by("name")
        currencies = apply_scope(Currency.objects.filter(is_active=True)).order_by("code")
        users_qs = apply_scope(
            UserModel.objects.all()
        ).order_by("fullName", "name", "username")
        financial_years = apply_scope(
            FinancialYear.objects.all()
        ).order_by("-from_date")
        products_qs = apply_scope(
            Product.objects.all()
        ).prefetch_related(
            "unit_prices",
            "unit_prices__measuring_unit",
            "units",
            "units__unit",
        )
        units_qs = apply_scope(
            Unit.objects.filter(status=True)
        ).order_by("name")

        def user_label(u):
            return u.fullName or u.name or u.username or u.email or ""

        products_payload = []
        for p in products_qs:
            unit_prices = []
            for up in p.unit_prices.all():
                if up.measuring_unit is None:
                    continue
                unit_prices.append(
                    {
                        "unit_id": up.measuring_unit_id,
                        "unit_name": up.measuring_unit.name,
                        "sales_price": str(up.sales_price or 0),
                        "purchase_price": str(up.purchase_price or 0),
                    }
                )
            product_units = []
            for pu in p.units.all():
                if pu.unit is None:
                    continue
                product_units.append(
                    {
                        "unit_id": pu.unit_id,
                        "unit_name": pu.unit.name,
                        "is_default_selling": bool(pu.is_default_selling),
                        "is_selling_unit": bool(pu.is_selling_unit),
                        "is_default": bool(pu.is_default),
                        "conversion_to_base": str(pu.conversion_to_base or 1),
                    }
                )
            products_payload.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "code": p.code,
                    "is_multiple_unit_enabled": bool(
                        getattr(p, "is_multiple_unit_enabled", False)
                    ),
                    "selling_unit_id": getattr(p, "selling_unit_id", None),
                    "selling_unit_name": (
                        p.selling_unit.name if p.selling_unit else None
                    ),
                    "default_rate": str(p.priceSale or p.price or 0),
                    "unit_prices": unit_prices,
                    "product_units": product_units,
                }
            )

        return Response(
            {
                "customers": [
                    {"id": str(c.id), "name": c.name}
                    for c in customers
                ],
                "currencies": CurrencySerializer(currencies, many=True).data,
                "users": [
                    {"id": u.id, "name": user_label(u)}
                    for u in users_qs
                ],
                "financial_years": [
                    {"id": fy.id, "name": fy.name} for fy in financial_years
                ],
                "products": products_payload,
                "units": [
                    {"id": u.id, "name": u.name} for u in units_qs
                ],
            }
        )
