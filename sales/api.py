from rest_framework.decorators import permission_classes, action, api_view
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal

from .models import Sale, InvoiceItem, Refund, RefundItem
from .serializers import (
    SaleSerializer,
    InvoiceSerialzer,
    SalePostSerializer,
    POSOrderSerializer,
    POSOrderCreateSerializer,
    POSOrderItemSerializer,
    RefundCreateSerializer,
    RefundSerializer,
    RefundListSerializer,
)
from rest_framework import serializers, viewsets, permissions
from rest_framework import generics
from django.shortcuts import render
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from django.conf import settings
from datetime import datetime, time, timedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from common.drf_scoping import (
    apply_company_branch_scope,
    get_allowed_branch_ids_for_user,
    get_company_ids_for_user,
    is_unrestricted_user,
)
from common.permissions import IsPOSOperator, IsBranchManagerOrAbove

from .refund_utils import recalculate_sale_is_return


def _parse_ymd(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _get_date_window(request):
    """Return an aware datetime window [start_dt, end_dt) based on query params.

    Supported:
    - date_range=today|week|month (defaults to today)
    - date_from=YYYY-MM-DD
    - date_to=YYYY-MM-DD (inclusive)
    """
    tz = timezone.get_current_timezone()

    date_from = _parse_ymd(request.query_params.get("date_from"))
    date_to = _parse_ymd(request.query_params.get("date_to"))

    if date_from or date_to:
        start_date = date_from or timezone.localdate()
        end_date = date_to or timezone.localdate()
    else:
        date_range = request.query_params.get("date_range", "today")
        today = timezone.localdate()
        if date_range == "week":
            start_date, end_date = today - timedelta(days=7), today
        elif date_range == "month":
            start_date, end_date = today - timedelta(days=30), today
        else:
            start_date, end_date = today, today

    start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    end_dt = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), time.min), tz
    )
    return start_dt, end_dt


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def pos_sales_summary(request):
    """POS Sales summary API based on `sales.Sale`.

    This is intentionally lightweight (no full order payloads).
    It matches POS Order List semantics:
    - Only include records where `order_number` is present
    - Filter by an explicit `order_time` datetime range

    Query params:
    - date_range=today|week|month
    - date_from=YYYY-MM-DD, date_to=YYYY-MM-DD
    - company_id/companyId, branch_id/branchId (for users with access)
    """

    start_dt, end_dt = _get_date_window(request)

    base_qs = Sale.objects.filter(
        order_number__isnull=False,
        order_time__gte=start_dt,
        order_time__lt=end_dt,
    )

    scoped_qs = apply_company_branch_scope(
        request=request,
        queryset=base_qs,
        company_id_field="companyId_id",
        branch_id_field="branch_id",
    )

    totals = scoped_qs.aggregate(
        total_sales=Sum("totalAmount"),
        total_orders=Count("id"),
        total_items_sold=Sum("totalQty"),
    )

    total_sales = float(totals.get("total_sales") or 0)
    total_orders = int(totals.get("total_orders") or 0)
    total_items_sold = int(totals.get("total_items_sold") or 0)
    avg_order_value = float(total_sales / total_orders) if total_orders else 0.0

    payment_rows = (
        scoped_qs.exclude(payment_method__isnull=True)
        .exclude(payment_method__exact="")
        .values("payment_method")
        .annotate(amount=Sum("totalAmount"), count=Count("id"))
        .order_by("-amount")
    )
    payment_breakdown = []
    for row in payment_rows:
        method = (row.get("payment_method") or "unknown").lower()
        amount = float(row.get("amount") or 0)
        count = int(row.get("count") or 0)
        payment_breakdown.append(
            {
                "method": method,
                "amount": amount,
                "count": count,
                "percentage": (
                    float((amount / total_sales) * 100) if total_sales else 0.0
                ),
            }
        )

    trend_rows = (
        scoped_qs.annotate(day=TruncDate("order_time"))
        .values("day")
        .annotate(sales=Sum("totalAmount"), orders=Count("id"))
        .order_by("day")
    )
    daily_trend = [
        {
            "date": (row.get("day").isoformat() if row.get("day") else None),
            "sales": float(row.get("sales") or 0),
            "orders": int(row.get("orders") or 0),
        }
        for row in trend_rows
    ]

    recent_sales_qs = scoped_qs.select_related("customer").order_by("-order_time")[:10]
    recent_sales = []
    for sale in recent_sales_qs:
        recent_sales.append(
            {
                "order_number": sale.order_number,
                "amount": float(sale.totalAmount or 0),
                "status": sale.status,
                "payment_method": (sale.payment_method or "").lower(),
                "order_time": sale.order_time.isoformat() if sale.order_time else None,
                "customer": getattr(sale.customer, "name", None),
            }
        )

    return Response(
        {
            "success": True,
            "data": {
                "window": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
                "totals": {
                    "total_sales": total_sales,
                    "total_orders": total_orders,
                    "avg_order_value": avg_order_value,
                    "total_items_sold": total_items_sold,
                    "currency": "BDT",
                },
                "payment_breakdown": payment_breakdown,
                "daily_trend": daily_trend,
                "recent_sales": recent_sales,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def pos_settings(request):
    """Return POS runtime settings used by the frontend.

    Keep this endpoint small and safe: only non-sensitive configuration.
    """

    try:
        cash_waiver_max = getattr(settings, "POS_CASH_WAIVER_MAX", Decimal("0"))
    except Exception:
        cash_waiver_max = Decimal("0")

    return Response(
        {
            "success": True,
            "data": {
                "cash_waiver_max": float(cash_waiver_max or 0),
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_invoice_view(request, token):
    """
    Public endpoint for viewing invoice details via secure token.
    No authentication required - anyone with the token can view.
    Returns ONLY invoice information, nothing else.
    Token expires after 30 days from order creation.
    """
    try:
        from datetime import timedelta
        from django.utils import timezone

        # Find order by share token
        order = (
            Sale.objects.filter(share_token=token)
            .select_related("customer", "companyId", "branch")
            .prefetch_related("items")
            .first()
        )

        if not order:
            return Response(
                {"success": False, "error": "Invalid or expired invoice link"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if token has expired (30 days from order creation)
        if order.createDate:
            expiry_date = order.createDate + timedelta(days=30)
            if timezone.now() > expiry_date:
                return Response(
                    {
                        "success": False,
                        "error": "This invoice link has expired. Invoice links are valid for 30 days.",
                    },
                    status=status.HTTP_410_GONE,
                )

        # Serialize order data - using POSOrderSerializer but limiting fields
        serializer = POSOrderSerializer(order)
        data = serializer.data

        # Return only invoice-related fields for security
        invoice_data = {
            "success": True,
            "invoice": {
                "order_number": data.get("order_number"),
                "order_type": data.get("order_type"),
                "order_type_display": data.get("order_type_display"),
                "status": data.get("status"),
                "status_display": data.get("status_display"),
                "payment_method": data.get("payment_method"),
                "is_paid": data.get("is_paid"),
                "order_time": data.get("order_time"),
                "company_name": data.get("company_name"),
                "branch_name": data.get("branch_name"),
                "store": data.get("store"),
                "table_number": data.get("table_number"),
                "customer_name": data.get("customer_name"),
                "customer_phone": data.get("customer_phone"),
                "customer_address": data.get("customer_address"),
                "display_name": data.get("display_name"),
                "subtotal": data.get("subtotal"),
                "tax_amount": data.get("tax_amount"),
                "discount_amount": data.get("discount_amount"),
                "service_charge_amount": data.get("service_charge_amount"),
                "tip_amount": data.get("tip_amount"),
                "total_amount": data.get("total_amount"),
                "currency": data.get("currency", "BDT"),
                "order_items": data.get("order_items", []),
                "notes": order.notes,
            },
        }

        return Response(invoice_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"success": False, "error": "Failed to retrieve invoice"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class SaleViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = SaleSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        queryset = Sale.objects.all()
        return apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )


class SalePostSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = SalePostSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        queryset = Sale.objects.all()
        return apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

    def _resolve_company(self):
        user = self.request.user
        if getattr(user, "companyId", None):
            return user.companyId

        branches = user.branchAccess.select_related("company")
        company_ids = set(branches.values_list("company_id", flat=True))
        if len(company_ids) == 1 and branches.exists():
            return branches.first().company

        return None

    def perform_create(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        company = self._resolve_company()
        if not company:
            raise PermissionDenied("User is not associated with a company")

        branch = serializer.validated_data.get("branch")
        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if branch is not None:
            if str(branch.company_id) != str(company.id):
                raise PermissionDenied("Branch does not belong to your company")
            if (
                allowed_branch_ids is not None
                and str(branch.id) not in allowed_branch_ids
            ):
                raise PermissionDenied("You do not have access to this branch")
        elif allowed_branch_ids is not None and len(allowed_branch_ids) == 1:
            branch_id = next(iter(allowed_branch_ids))
            branch = user.branchAccess.get(id=branch_id)

        serializer.save(companyId=company, branch=branch)

    def perform_update(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        company_ids = get_company_ids_for_user(user)
        if not company_ids or str(serializer.instance.companyId_id) not in company_ids:
            raise PermissionDenied("You do not have access to this sale")

        serializer.save(companyId=serializer.instance.companyId)


class SaleItemSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = InvoiceSerialzer

    # http_method_names= ['get']
    def get_queryset(self):
        queryset = InvoiceItem.objects.all()
        return apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="sell_invoice__companyId_id",
            branch_id_field="sell_invoice__branch_id",
        )


# POS-specific API Views
class POSOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for POS orders - handles order creation, updates, and listing
    """

    queryset = Sale.objects.all()
    serializer_class = POSOrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsPOSOperator]

    def get_queryset(self):
        """Filter orders based on query parameters"""
        queryset = Sale.objects.filter(order_number__isnull=False).order_by(
            "-order_time"
        )

        # Filter by order type
        order_type = self.request.query_params.get("order_type")
        if order_type:
            queryset = queryset.filter(order_type=order_type)

        # Filter by status
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by payment method
        payment_method = self.request.query_params.get("payment_method")
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        # Filter by table number
        table_number = self.request.query_params.get("table_number")
        if table_number:
            queryset = queryset.filter(table_number=table_number)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        # IMPORTANT: Avoid `order_time__date` here.
        # On SQLite, date extraction is effectively UTC and can drop early-morning
        # local (Asia/Dhaka) orders from "today". Use an explicit datetime range.
        def _parse_ymd(value: str | None):
            if not value:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None

        tz = timezone.get_current_timezone()
        start_date = _parse_ymd(date_from)
        end_date = _parse_ymd(date_to)

        if start_date:
            start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
            queryset = queryset.filter(order_time__gte=start_dt)

        if end_date:
            # inclusive end_date => < next day 00:00
            end_dt = timezone.make_aware(
                datetime.combine(end_date + timedelta(days=1), time.min), tz
            )
            queryset = queryset.filter(order_time__lt=end_dt)

        # Apply company/branch scoping
        queryset = apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

        # STRICT BRANCH FILTERING: When a specific branch_id is requested,
        # exclude orders with NULL branch to prevent cross-branch data leakage
        branch_id = self.request.query_params.get(
            "branch_id"
        ) or self.request.query_params.get("branchId")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        return queryset

    def _resolve_company(self):
        user = self.request.user
        if getattr(user, "companyId", None):
            return user.companyId

        branches = user.branchAccess.select_related("company")
        company_ids = set(branches.values_list("company_id", flat=True))
        if len(company_ids) == 1 and branches.exists():
            return branches.first().company

        return None

    def get_serializer_class(self):
        """Use different serializer for creation"""
        if self.action == "create":
            return POSOrderCreateSerializer
        return POSOrderSerializer

    def create(self, request, *args, **kwargs):
        """Create new POS order with atomic transaction and retry logic"""
        from django.db import transaction
        import time
        import logging

        logger = logging.getLogger(__name__)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"POS Order validation errors: {serializer.errors}")
            logger.warning(f"POS Order request data: {request.data}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        company = None
        branch = None
        branch_id = request.query_params.get("branch_id") or request.query_params.get(
            "branchId"
        )
        if not is_unrestricted_user(request.user):
            company = self._resolve_company()
            if not company:
                raise PermissionDenied("User is not associated with a company")

            allowed_branch_ids = get_allowed_branch_ids_for_user(request.user)
            allowed_branch_ids_str = (
                {str(i) for i in allowed_branch_ids}
                if allowed_branch_ids is not None
                else None
            )
            if branch_id:
                branch_id_str = str(branch_id)
                if (
                    allowed_branch_ids_str is not None
                    and branch_id_str not in allowed_branch_ids_str
                ):
                    raise PermissionDenied("You do not have access to this branch")

                if allowed_branch_ids_str is not None:
                    branch = request.user.branchAccess.filter(id=branch_id).first()
                else:
                    # allowed_branch_ids=None means "all branches within company".
                    # Still resolve and persist the branch for POS billing.
                    from company.models import Branch as CompanyBranch

                    branch = (
                        CompanyBranch.objects.select_related("company")
                        .filter(id=branch_id, company=company)
                        .first()
                    )

                if not branch:
                    raise PermissionDenied("Invalid branch")
            elif (
                allowed_branch_ids_str is not None and len(allowed_branch_ids_str) == 1
            ):
                only_branch_id = next(iter(allowed_branch_ids_str))
                branch = request.user.branchAccess.get(id=only_branch_id)

        else:
            # For unrestricted users, allow optional branch_id to be recorded
            # (useful for reporting/filtering).
            if branch_id:
                from company.models import Branch as CompanyBranch

                branch = (
                    CompanyBranch.objects.select_related("company")
                    .filter(id=branch_id)
                    .first()
                )
                if branch and not company:
                    company = branch.company

        # Retry logic for order number conflicts
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Create order with atomic transaction
                    order = serializer.save(companyId=company, branch=branch)

                    # Generate unique order number with retry logic
                    if not order.order_number:
                        order.generate_order_number()

                        # Double-check for uniqueness with select_for_update
                        existing_order = (
                            Sale.objects.select_for_update()
                            .filter(order_number=order.order_number)
                            .exclude(id=order.id)
                            .first()
                        )

                        if existing_order:
                            # Force regenerate if duplicate found
                            order.order_number = None
                            order.generate_order_number()

                    order.save()

                    # Return successful response
                    response_serializer = POSOrderSerializer(order)
                    return Response(
                        response_serializer.data, status=status.HTTP_201_CREATED
                    )

            except Exception as e:
                error_message = str(e).lower()
                if (
                    "unique constraint failed" in error_message
                    and "order_number" in error_message
                ):
                    if attempt < max_retries - 1:
                        # Wait before retry with exponential backoff
                        time.sleep(0.1 * (2**attempt))
                        continue
                    else:
                        return Response(
                            {
                                "error": "Unable to generate unique order number after multiple attempts. Please try again.",
                                "code": "ORDER_NUMBER_CONFLICT",
                            },
                            status=status.HTTP_409_CONFLICT,
                        )
                else:
                    # Re-raise non-order-number errors
                    raise e

        # Fallback error (should not reach here)
        return Response(
            {"error": "Order creation failed after retries"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        """Update order status"""
        order = self.get_object()
        new_status = request.data.get("status")

        if new_status not in dict(Sale._meta.get_field("status").choices):
            return Response(
                {"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status

        # Update timestamps based on status
        if new_status == "ready" and not order.ready_time:
            order.ready_time = timezone.now()
        elif new_status == "served" and not order.served_time:
            order.served_time = timezone.now()
        elif new_status == "paid":
            order.is_paid = True

        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def print_kot(self, request, pk=None):
        """Mark KOT as printed"""
        order = self.get_object()
        order.kot_printed = True
        order.save()

        return Response({"message": "KOT printed successfully"})

    @action(detail=False, methods=["get"])
    def kitchen_orders(self, request):
        """Get orders for kitchen display"""
        orders = (
            self.get_queryset()
            .filter(status__in=["confirmed", "preparing"])
            .prefetch_related("items")
        )

        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_items(self, request, pk=None):
        """Add items to an existing order"""
        order = self.get_object()

        if order.status in ["paid", "cancelled", "served"]:
            return Response(
                {"error": "Cannot modify order in current status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_data = request.data.get("items", [])
        if not items_data:
            return Response(
                {"error": "No items provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Add new items to the order
        for item_data in items_data:
            # Find or create invoice item
            existing_item = InvoiceItem.objects.filter(
                sell_invoice=order, product_id=item_data.get("id")
            ).first()

            if existing_item:
                # Update quantity if item already exists
                existing_item.quantity += item_data.get("quantity", 1)
                existing_item.total_price = (
                    existing_item.quantity * existing_item.unit_price
                )
                existing_item.save()
            else:
                # Create new invoice item
                from products.models import Product

                try:
                    product = Product.objects.get(id=item_data.get("id"))
                    InvoiceItem.objects.create(
                        sell_invoice=order,
                        product=product,
                        title=item_data.get("name", product.name),
                        category=item_data.get("category", ""),
                        quantity=item_data.get("quantity", 1),
                        unit_price=float(
                            item_data.get("price", product.sale_price or 0)
                        ),
                        total_price=float(item_data.get("quantity", 1))
                        * float(item_data.get("price", product.sale_price or 0)),
                        preparation_time=item_data.get("preparation_time", 15),
                    )
                except Product.DoesNotExist:
                    return Response(
                        {"error": f"Product {item_data.get('id')} not found"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Recalculate order totals
        order.calculate_totals()
        order.save()

        # Return updated order
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def remove_items(self, request, pk=None):
        """Remove items from an existing order"""
        order = self.get_object()

        if order.status in ["paid", "cancelled", "served"]:
            return Response(
                {"error": "Cannot modify order in current status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item_ids = request.data.get("item_ids", [])
        if not item_ids:
            return Response(
                {"error": "No item IDs provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Remove specified items
        InvoiceItem.objects.filter(sell_invoice=order, id__in=item_ids).delete()

        # Recalculate order totals
        order.calculate_totals()
        order.save()

        # Return updated order
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Override update to handle order modifications"""
        order = self.get_object()

        if order.status in ["paid", "cancelled", "served"]:
            return Response(
                {"error": "Cannot modify order in current status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Handle items update if provided
        items_data = request.data.get("items")
        if items_data is not None:
            # Clear existing items and add new ones
            order.items.all().delete()

            for item_data in items_data:
                from products.models import Product

                try:
                    product = Product.objects.get(
                        id=item_data.get("menu_item_id", item_data.get("id"))
                    )
                    InvoiceItem.objects.create(
                        sell_invoice=order,
                        product=product,
                        title=item_data.get(
                            "title", item_data.get("name", product.name)
                        ),
                        category=item_data.get("category", ""),
                        quantity=item_data.get("quantity", 1),
                        unit_price=float(
                            item_data.get(
                                "unit_price",
                                item_data.get("price", product.sale_price or 0),
                            )
                        ),
                        total_price=float(
                            item_data.get(
                                "total_price",
                                item_data.get("quantity", 1)
                                * item_data.get(
                                    "unit_price",
                                    item_data.get("price", product.sale_price or 0),
                                ),
                            )
                        ),
                        preparation_time=item_data.get("preparation_time", 15),
                    )
                except (Product.DoesNotExist, ValueError) as e:
                    return Response(
                        {"error": f"Invalid item data: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Update other order fields
        for field in ["notes", "status", "payment_method"]:
            if field in request.data:
                setattr(order, field, request.data[field])

        # Recalculate totals and save
        order.calculate_totals()
        order.save()

        # Return updated order
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def active_orders(self, request):
        """Get active orders (not completed)"""
        orders = self.get_queryset().filter(
            status__in=["pending", "confirmed", "preparing", "ready"]
        )

        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="refunds")
    def refunds(self, request, pk=None):
        """List refunds for a POS order."""
        order = self.get_object()
        refunds_qs = Refund.objects.filter(sale=order).order_by("-created_at")
        return Response(RefundSerializer(refunds_qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="refund")
    def refund(self, request, pk=None):
        """Create a refund (partial/full) for a POS order."""
        from django.db import transaction
        from django.db.models import Sum

        # Refunds are sensitive: require manager+ (unless unrestricted).
        if not (
            is_unrestricted_user(request.user)
            or IsBranchManagerOrAbove().has_permission(request, self)
        ):
            raise PermissionDenied("Only managers/admins can create refunds")

        order = self.get_object()

        # Professional guard: only allow refunds for paid orders.
        # (UI expectation: refunds/returns apply to completed/paid bills.)
        if not order.is_paid and (order.status != "paid"):
            return Response(
                {"error": "Only paid orders can be refunded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = RefundCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        items_payload = payload.validated_data.get("items") or []
        reason = payload.validated_data.get("reason") or ""
        payment_method = (
            payload.validated_data.get("payment_method") or order.payment_method
        )

        # Build a map of refundable quantities per invoice item
        order_items = list(order.items.all())
        if not order_items:
            return Response(
                {"error": "Order has no items to refund"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        already_refunded = {
            str(row["invoice_item"]).lower(): int(row["qty"] or 0)
            for row in RefundItem.objects.filter(invoice_item__in=order_items)
            .values("invoice_item")
            .annotate(qty=Sum("quantity"))
        }

        refundable_by_id = {}
        for item in order_items:
            refunded_qty = already_refunded.get(str(item.id).lower(), 0)
            refundable_by_id[str(item.id)] = max(
                int(item.quantity or 0) - refunded_qty, 0
            )

        # If items not specified, refund everything refundable.
        if not items_payload:
            items_payload = [
                {"invoice_item_id": item.id, "quantity": refundable_by_id[str(item.id)]}
                for item in order_items
                if refundable_by_id[str(item.id)] > 0
            ]

        # Validate requested quantities
        requested = []
        for line in items_payload:
            invoice_item_id = str(line["invoice_item_id"])
            qty = int(line["quantity"])

            available = refundable_by_id.get(invoice_item_id)
            if available is None:
                return Response(
                    {"error": f"Invalid invoice_item_id: {invoice_item_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if qty <= 0:
                continue
            if qty > available:
                return Response(
                    {
                        "error": "Refund quantity exceeds available quantity",
                        "invoice_item_id": invoice_item_id,
                        "available": available,
                        "requested": qty,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            requested.append((invoice_item_id, qty))

        if not requested:
            return Response(
                {"error": "Nothing to refund"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_by_id = {str(i.id): i for i in order_items}

        with transaction.atomic():
            refund = Refund.objects.create(
                sale=order,
                created_by=request.user,
                reason=reason,
                payment_method=payment_method,
                total_amount=0,
            )

            total_amount = Decimal("0.00")
            for invoice_item_id, qty in requested:
                inv_item = items_by_id[invoice_item_id]
                unit_price = Decimal(str(inv_item.price or 0))
                line_total = unit_price * qty

                RefundItem.objects.create(
                    refund=refund,
                    invoice_item=inv_item,
                    quantity=qty,
                    unit_price=unit_price,
                    total=line_total,
                )

                total_amount += line_total

            refund.total_amount = float(total_amount)
            refund.save(update_fields=["total_amount"])

            # Professional: mark as returned only if fully refunded.
            recalculate_sale_is_return(order)

        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)


class POSOrderItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual order items
    """

    queryset = InvoiceItem.objects.all()
    serializer_class = POSOrderItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsPOSOperator]

    def get_queryset(self):
        """Filter items by order if specified"""
        queryset = InvoiceItem.objects.all().order_by("-createDate")

        order_id = self.request.query_params.get("order_id")
        if order_id:
            queryset = queryset.filter(sell_invoice__id=order_id)

        return apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="sell_invoice__companyId_id",
            branch_id_field="sell_invoice__branch_id",
        )

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        """Update item status"""
        item = self.get_object()
        new_status = request.data.get("status")

        valid_statuses = ["ordered", "preparing", "ready", "served"]
        if new_status not in valid_statuses:
            return Response(
                {"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST
            )

        item.status = new_status

        # Update timestamps
        if new_status == "ready":
            item.prepared_at = timezone.now()
        elif new_status == "served":
            item.served_at = timezone.now()

        item.save()

        serializer = self.get_serializer(item)
        return Response(serializer.data)


class POSRefundViewSet(viewsets.ModelViewSet):
    """Global refund list (professional view) with scoping + filters."""

    queryset = Refund.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsBranchManagerOrAbove]
    http_method_names = ["get", "delete", "head", "options"]

    def get_queryset(self):
        qs = Refund.objects.select_related(
            "sale", "created_by", "sale__branch"
        ).order_by("-created_at")

        # Filter by creator (refund created_by)
        created_by = (
            self.request.query_params.get("created_by")
            or self.request.query_params.get("created_by_id")
            or self.request.query_params.get("creator_id")
        )
        if created_by:
            qs = qs.filter(created_by_id=created_by)

        payment_method = self.request.query_params.get("payment_method")
        if payment_method:
            qs = qs.filter(payment_method=payment_method)

        # Date filters (YYYY-MM-DD) using timezone-aware datetime ranges.
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        def _parse_ymd(value: str | None):
            if not value:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None

        tz = timezone.get_current_timezone()
        start_date = _parse_ymd(date_from)
        end_date = _parse_ymd(date_to)

        if start_date:
            start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
            qs = qs.filter(created_at__gte=start_dt)

        if end_date:
            end_dt = timezone.make_aware(
                datetime.combine(end_date + timedelta(days=1), time.min), tz
            )
            qs = qs.filter(created_at__lt=end_dt)

        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="sale__companyId_id",
            branch_id_field="sale__branch_id",
            # Do not accept branch_id as a query filter here.
            branch_param_names=(),
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RefundSerializer
        return RefundListSerializer

    def list(self, request, *args, **kwargs):
        """List refunds with a lightweight summary for current filters."""
        from django.db.models import Sum

        queryset = self.filter_queryset(self.get_queryset())
        summary_total = queryset.aggregate(total_amount=Sum("total_amount")).get(
            "total_amount"
        )
        summary = {
            "total_amount": float(summary_total or 0),
        }

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            resp = self.get_paginated_response(serializer.data)
            # DRF Response.data is a dict for paginated responses.
            resp.data["summary"] = summary
            return resp

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "count": len(serializer.data),
                "results": serializer.data,
                "summary": summary,
            }
        )

    def destroy(self, request, *args, **kwargs):
        """Delete a refund (professional correction flow).

        Allowed for:
        - Unrestricted users
        - The refund creator

        After deletion, the sale's `is_return` flag is recalculated.
        """
        instance = self.get_object()
        if not (
            is_unrestricted_user(request.user)
            or instance.created_by_id == request.user.id
        ):
            raise PermissionDenied("You do not have permission to delete this refund")

        sale = instance.sale
        resp = super().destroy(request, *args, **kwargs)
        if sale:
            recalculate_sale_is_return(sale)
        return resp
