from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from datetime import datetime, timedelta
from datetime import time
from decimal import Decimal
import json

from common.drf_scoping import (
    get_allowed_branch_ids_for_user,
    get_company_ids_for_user,
    is_unrestricted_user,
)

# Import models from other apps - with error handling
# These will be imported lazily inside functions to avoid startup errors


def _user_company_pk(user):
    """Return the user's company primary key as an int."""
    company_id = getattr(user, "companyId_id", None)
    if isinstance(company_id, int):
        return company_id
    company_obj = getattr(user, "companyId", None)
    if company_obj is None:
        return None
    if isinstance(company_obj, int):
        return company_obj
    if isinstance(company_obj, str) and company_obj.isdigit():
        return int(company_obj)
    pk = getattr(company_obj, "pk", None)
    return pk if isinstance(pk, int) else None


def _user_branch_pk(user):
    """Return the user's branch primary key as an int.

    Note: authenticator.User doesn't have a single branch FK; it uses `branchAccess`.
    If the user has exactly one allowed branch, treat it as the active branch.
    """
    try:
        branches = user.branchAccess.all()
        if branches.count() == 1:
            only_branch = branches.first()
            return only_branch.id if only_branch else None
    except Exception:
        pass
    return None


def get_model_safe(app_name, model_name):
    """Safely import a model at runtime"""
    try:
        from django.apps import apps

        return apps.get_model(app_name, model_name)
    except (ImportError, LookupError):
        return None


def safe_model_query(model_name, app_name=None):
    """Safely query a model, return empty result if model is not available"""

    # Try to get the model dynamically
    if app_name:
        model = get_model_safe(app_name, model_name)
    else:
        # Try common app names for each model
        model_app_mapping = {
            "Sale": "sales",
            "InvoiceItem": "sales",
            "Order": "order",
            "OrderItem": "order",
            "Product": "products",
            "Stock": "stock",
            "Purchase": "purchase",
            "Expense": "expense",
            "Customer": "customers",
            "Income": "income",
            "Company": "company",
            "Branch": "company",
        }

        app_name = model_app_mapping.get(model_name, model_name.lower())
        if model_name == "OrderItem":
            # Special case for OrderItem which is actually named 'Item'
            model = get_model_safe(app_name, "Item")
        else:
            model = get_model_safe(app_name, model_name)

    if model is None:
        # Return a mock queryset-like object
        class MockQuerySet:
            def filter(self, *args, **kwargs):
                return self

            def exclude(self, *args, **kwargs):
                return self

            def order_by(self, *args, **kwargs):
                return self

            def aggregate(self, **kwargs):
                return {k: 0 for k in kwargs.keys()}

            def count(self):
                return 0

            def __getitem__(self, key):
                return []

            def __iter__(self):
                return iter([])

            def values(self, *args, **kwargs):
                return self

            def annotate(self, **kwargs):
                return self

            def select_related(self, *args, **kwargs):
                return self

        return MockQuerySet()
    return model.objects


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_full_summary(request):
    """
    Get complete dashboard summary for Mega Supershop POS in a single API call.
    Returns: metrics, sales trends, top products, low stock alerts, recent sales, financial summary.
    """
    try:
        user = request.user

        # Optional explicit scoping (for users who can switch company/branch in UI)
        requested_company_id = request.GET.get("company_id") or request.GET.get(
            "companyId"
        )
        requested_branch_id = request.GET.get("branch_id") or request.GET.get(
            "branchId"
        )

        company_pk = None
        branch_pk = None

        if requested_company_id is not None and str(requested_company_id).isdigit():
            company_pk = int(str(requested_company_id))

        if requested_branch_id is not None and str(requested_branch_id).isdigit():
            branch_pk = int(str(requested_branch_id))

        if not is_unrestricted_user(user):
            allowed_company_ids = get_company_ids_for_user(user)
            allowed_branch_ids = get_allowed_branch_ids_for_user(user)

            # Validate requested company
            if company_pk is not None:
                if (
                    not allowed_company_ids
                    or str(company_pk) not in allowed_company_ids
                ):
                    return Response(
                        {
                            "success": False,
                            "error": "You do not have access to this company",
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            else:
                company_pk = _user_company_pk(user)

            # Validate requested branch
            if branch_pk is not None:
                if (
                    allowed_branch_ids is not None
                    and str(branch_pk) not in allowed_branch_ids
                ):
                    return Response(
                        {
                            "success": False,
                            "error": "You do not have access to this branch",
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

                # Ensure branch belongs to company if both provided
                Branch = get_model_safe("company", "Branch")
                if Branch is not None and company_pk is not None:
                    branch_obj = (
                        Branch.objects.filter(id=branch_pk).only("company_id").first()
                    )
                    if branch_obj and str(branch_obj.company_id) != str(company_pk):
                        return Response(
                            {
                                "success": False,
                                "error": "Branch does not belong to selected company",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            else:
                branch_pk = _user_branch_pk(user)
        else:
            # Unrestricted users can scope via query params; otherwise no scope
            if company_pk is None:
                company_pk = _user_company_pk(user)
            if branch_pk is None:
                branch_pk = _user_branch_pk(user)

        # Get query parameters
        date_range = request.GET.get("date_range", "today")

        # Calculate date filter
        today = timezone.now().date()
        now = timezone.now()

        if date_range == "today":
            start_date = today
            end_date = today
        elif date_range == "week":
            start_date = today - timedelta(days=7)
            end_date = today
        elif date_range == "month":
            start_date = today - timedelta(days=30)
            end_date = today
        else:
            start_date = today
            end_date = today

        # Build filters for Sale model.
        # IMPORTANT: To match the POS Order List (`/api/pos/orders`), only include
        # POS orders that have an order_number and use order_time datetime ranges.
        tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
        end_dt = timezone.make_aware(
            datetime.combine(end_date + timedelta(days=1), time.min), tz
        )

        sale_filters = {
            "order_number__isnull": False,
            "order_time__gte": start_dt,
            "order_time__lt": end_dt,
        }
        if company_pk:
            sale_filters["companyId_id"] = company_pk
        if branch_pk:
            sale_filters["branch_id"] = branch_pk

        # ===== 1. KEY METRICS =====
        sales_data = (
            safe_model_query("Sale")
            .filter(**sale_filters)
            .aggregate(
                total_sales=Sum("totalAmount"),
                total_orders=Count("id"),
                avg_order_value=Avg("totalAmount"),
                total_items=Sum("totalQty"),
            )
        )

        # Yesterday/previous period comparison
        if date_range == "today":
            prev_start = today - timedelta(days=1)
            prev_end = prev_start
        else:
            period_days = (end_date - start_date).days + 1
            prev_end = start_date - timedelta(days=1)
            prev_start = prev_end - timedelta(days=period_days - 1)

        prev_start_dt = timezone.make_aware(datetime.combine(prev_start, time.min), tz)
        prev_end_dt = timezone.make_aware(
            datetime.combine(prev_end + timedelta(days=1), time.min), tz
        )
        prev_filters = sale_filters.copy()
        prev_filters["order_time__gte"] = prev_start_dt
        prev_filters["order_time__lt"] = prev_end_dt

        prev_sales = (
            safe_model_query("Sale")
            .filter(**prev_filters)
            .aggregate(total_sales=Sum("totalAmount"), total_orders=Count("id"))
        )

        current_sales = float(sales_data["total_sales"] or 0)
        previous_sales = float(prev_sales["total_sales"] or 0)
        current_orders = sales_data["total_orders"] or 0
        previous_orders = prev_sales["total_orders"] or 0

        sales_change = 0
        if previous_sales > 0:
            sales_change = ((current_sales - previous_sales) / previous_sales) * 100

        orders_change = 0
        if previous_orders > 0:
            orders_change = ((current_orders - previous_orders) / previous_orders) * 100

        # Customer count
        customer_filters = {}
        if company_pk:
            customer_filters["companyId_id"] = company_pk
        if branch_pk:
            customer_filters["branch_id"] = branch_pk
        total_customers = (
            safe_model_query("Customer").filter(**customer_filters).count()
        )

        # Product count
        product_filters = {}
        if company_pk:
            product_filters["companyId_id"] = company_pk
        if branch_pk:
            product_filters["branch_id"] = branch_pk
        total_products = safe_model_query("Product").filter(**product_filters).count()

        # Low stock count
        low_stock_filters = {"stock__lt": 10, "stock__gt": 0}
        if company_pk:
            low_stock_filters["product__companyId_id"] = company_pk
        if branch_pk:
            low_stock_filters["product__branch_id"] = branch_pk
        low_stock_count = safe_model_query("Stock").filter(**low_stock_filters).count()

        metrics = {
            "today_sales": {
                "amount": current_sales,
                "currency": "BDT",
                "change_percentage": round(sales_change, 1),
                "change_type": "increase" if sales_change >= 0 else "decrease",
            },
            "total_orders": {
                "count": current_orders,
                "change_percentage": round(orders_change, 1),
                "change_type": "increase" if orders_change >= 0 else "decrease",
            },
            "avg_order_value": {
                "amount": float(sales_data["avg_order_value"] or 0),
                "currency": "BDT",
            },
            "total_items_sold": sales_data["total_items"] or 0,
            "total_customers": total_customers,
            "total_products": total_products,
            "low_stock_alerts": low_stock_count,
        }

        # ===== 2. WEEKLY SALES TREND =====
        weekly_trend = []
        for i in range(7):
            date = today - timedelta(days=6 - i)
            day_start_dt = timezone.make_aware(datetime.combine(date, time.min), tz)
            day_end_dt = timezone.make_aware(
                datetime.combine(date + timedelta(days=1), time.min), tz
            )
            day_filters = sale_filters.copy()
            day_filters["order_time__gte"] = day_start_dt
            day_filters["order_time__lt"] = day_end_dt

            day_data = (
                safe_model_query("Sale")
                .filter(**day_filters)
                .aggregate(total=Sum("totalAmount"), count=Count("id"))
            )
            weekly_trend.append(
                {
                    "day": date.strftime("%a"),
                    "date": date.strftime("%Y-%m-%d"),
                    "sales": float(day_data["total"] or 0),
                    "orders": day_data["count"] or 0,
                }
            )

        # ===== 3. SALES BY PAYMENT METHOD =====
        payment_breakdown = list(
            safe_model_query("Sale")
            .filter(**sale_filters)
            .values("payment_method")
            .annotate(total=Sum("totalAmount"), count=Count("id"))
            .order_by("-total")
        )

        # ===== 4. TOP SELLING PRODUCTS =====
        top_products_data = []
        item_filters = {"order__createdAt__date__range": [start_date, end_date]}
        if company_pk:
            item_filters["product__companyId_id"] = company_pk
        if branch_pk:
            item_filters["product__branch_id"] = branch_pk

        top_items = (
            safe_model_query("OrderItem")
            .filter(**item_filters)
            .values("name", "price")
            .annotate(
                total_qty=Sum("quantity"),
                total_revenue=Sum("total"),
            )
            .order_by("-total_qty")[:10]
        )

        for item in top_items:
            if item["name"]:
                top_products_data.append(
                    {
                        "name": item["name"],
                        "quantity_sold": item["total_qty"] or 0,
                        "revenue": float(item["total_revenue"] or 0),
                        "price": float(item["price"] or 0),
                    }
                )

        # ===== 5. LOW STOCK ALERTS =====
        low_stock_items = list(
            safe_model_query("Stock")
            .filter(**low_stock_filters)
            .select_related("product")[:8]
        )

        low_stock_data = []
        for item in low_stock_items:
            product_name = "Unknown Product"
            if hasattr(item, "product") and item.product:
                product_name = getattr(item.product, "product_name", None) or getattr(
                    item.product, "name", "Unknown"
                )
            low_stock_data.append(
                {
                    "name": product_name,
                    "current_stock": item.stock if hasattr(item, "stock") else 0,
                    "reorder_level": 10,
                    "unit": "pcs",
                }
            )

        # ===== 6. RECENT SALES =====
        recent_sales_qs = (
            safe_model_query("Sale").filter(**sale_filters).order_by("-order_time")[:10]
        )

        recent_sales_data = []
        for sale in recent_sales_qs:
            customer_name = "Walk-in Customer"
            if hasattr(sale, "customer") and sale.customer:
                customer_name = getattr(sale.customer, "name", None) or getattr(
                    sale.customer, "fullName", "Customer"
                )

            recent_sales_data.append(
                {
                    "id": str(sale.id) if hasattr(sale, "id") else "",
                    "order_number": getattr(sale, "order_number", None)
                    or getattr(sale, "invoiceNumber", f"#{sale.id}"),
                    "customer": customer_name,
                    "amount": float(getattr(sale, "totalAmount", 0) or 0),
                    "status": getattr(sale, "status", "completed"),
                    "payment_method": getattr(sale, "payment_method", "cash"),
                    "items_count": getattr(sale, "totalQty", 0) or 0,
                    "created_at": (
                        sale.order_time.isoformat()
                        if hasattr(sale, "order_time") and sale.order_time
                        else (
                            sale.createDate.isoformat()
                            if hasattr(sale, "createDate") and sale.createDate
                            else now.isoformat()
                        )
                    ),
                }
            )

        # ===== 7. FINANCIAL SUMMARY =====
        expense_filters = {"created_at__date__range": [start_date, end_date]}
        # Expense has no direct tenant fields; scope via the Timestamp.user relation.
        if company_pk:
            expense_filters["user__companyId_id"] = company_pk
        if branch_pk:
            # User has M2M `branchAccess`, not a single branch FK.
            expense_filters["user__branchAccess__id"] = branch_pk

        expense_data = (
            safe_model_query("Expense")
            .filter(**expense_filters)
            .aggregate(total=Sum("amount"))
        )

        purchase_filters = {"created_at__date__range": [start_date, end_date]}
        # Purchase is scoped via its related product (and optionally via Timestamp.user)
        if company_pk:
            purchase_filters["product__companyId_id"] = company_pk
        if branch_pk:
            purchase_filters["product__branch_id"] = branch_pk

        purchase_data = (
            safe_model_query("Purchase")
            .filter(**purchase_filters)
            .aggregate(total=Sum("total_amount"))
        )

        total_expenses = float(expense_data["total"] or 0)
        total_purchases = float(purchase_data["total"] or 0)
        gross_profit = current_sales - total_purchases
        net_profit = gross_profit - total_expenses

        financial_summary = {
            "total_sales": current_sales,
            "total_purchases": total_purchases,
            "total_expenses": total_expenses,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "profit_margin": (
                round((net_profit / current_sales * 100), 1) if current_sales > 0 else 0
            ),
            "currency": "BDT",
        }

        # ===== 8. HOURLY SALES (for today) =====
        hourly_sales = []
        if date_range == "today":
            for hour in range(24):
                hour_start = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)

                hour_filters = sale_filters.copy()
                hour_filters["order_time__gte"] = hour_start
                hour_filters["order_time__lt"] = hour_end

                hour_data = (
                    safe_model_query("Sale")
                    .filter(**hour_filters)
                    .aggregate(total=Sum("totalAmount"), count=Count("id"))
                )

                if hour <= now.hour:
                    hourly_sales.append(
                        {
                            "hour": f"{hour:02d}:00",
                            "sales": float(hour_data["total"] or 0),
                            "orders": hour_data["count"] or 0,
                        }
                    )

        return Response(
            {
                "success": True,
                "data": {
                    "metrics": metrics,
                    "weekly_trend": weekly_trend,
                    "payment_breakdown": payment_breakdown,
                    "top_products": top_products_data,
                    "low_stock_alerts": low_stock_data,
                    "recent_sales": recent_sales_data,
                    "financial_summary": financial_summary,
                    "hourly_sales": hourly_sales,
                },
                "filters": {
                    "date_range": date_range,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "company_id": company_pk,
                    "branch_id": branch_pk,
                },
                "generated_at": now.isoformat(),
            }
        )

    except Exception as e:
        import traceback

        return Response(
            {"success": False, "error": str(e), "traceback": traceback.format_exc()},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_metrics(request):
    """
    Get key dashboard metrics: sales, orders, tables, average order value
    """
    try:
        # Get query parameters
        date_range = request.GET.get("date_range", "today")  # today, week, month

        # Calculate date filter
        today = timezone.now().date()
        if date_range == "today":
            start_date = today
            end_date = today
        elif date_range == "week":
            start_date = today - timedelta(days=7)
            end_date = today
        elif date_range == "month":
            start_date = today - timedelta(days=30)
            end_date = today
        else:
            start_date = today
            end_date = today

        # Filter by date only (company/branch not supported by current models)
        filters = {"createDate__date__range": [start_date, end_date]}

        # Calculate metrics
        # Today's Sales
        sales_data = (
            safe_model_query("Sale")
            .filter(**filters)
            .aggregate(
                total_sales=Sum("totalAmount"),
                total_orders=Count("id"),
                avg_order_value=Avg("totalAmount"),
            )
        )

        # Get yesterday's data for comparison
        yesterday_filters = filters.copy()
        if date_range == "today":
            yesterday = today - timedelta(days=1)
            yesterday_filters["createDate__date__range"] = [yesterday, yesterday]
        else:
            # For week/month, compare with previous period
            period_days = (end_date - start_date).days + 1
            prev_end = start_date - timedelta(days=1)
            prev_start = prev_end - timedelta(days=period_days)
            yesterday_filters["createDate__date__range"] = [prev_start, prev_end]

        yesterday_sales = (
            safe_model_query("Sale")
            .filter(**yesterday_filters)
            .aggregate(total_sales=Sum("totalAmount"))
        )  # Calculate percentage change
        today_sales = float(sales_data["total_sales"] or 0)
        yesterday_sales_amount = float(yesterday_sales["total_sales"] or 0)

        sales_change = 0
        if yesterday_sales_amount > 0:
            sales_change = (
                (today_sales - yesterday_sales_amount) / yesterday_sales_amount
            ) * 100

        # Active orders (orders that are not completed)
        active_orders = (
            safe_model_query("Order")
            .filter(
                status__in=["pending", "processing"],
            )
            .count()
        )

        # Active tables (mock data for now)
        total_tables = 32  # This should come from a table management system
        active_tables = 18  # This should be calculated based on current orders
        occupancy_rate = (active_tables / total_tables) * 100

        metrics = {
            "sales": {
                "amount": today_sales,
                "currency": "৳",
                "change_percentage": round(sales_change, 1),
                "change_type": "increase" if sales_change > 0 else "decrease",
                "period": date_range,
            },
            "orders": {
                "total": sales_data["total_orders"] or 0,
                "active": active_orders,
                "period": date_range,
            },
            "tables": {
                "active": active_tables,
                "total": total_tables,
                "occupancy_rate": round(occupancy_rate, 1),
            },
            "avg_order_value": {
                "amount": float(sales_data["avg_order_value"] or 0),
                "currency": "৳",
                "period": date_range,
            },
        }

        return Response(
            {
                "success": True,
                "data": metrics,
                "filters_applied": {
                    "date_range": date_range,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                },
            }
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sales_analytics(request):
    """
    Get sales analytics data for charts: weekly trends, category revenue
    """
    try:
        # Get query parameters
        chart_type = request.GET.get(
            "chart_type", "weekly"
        )  # weekly, monthly, category

        # No company/branch filters as models don't support them
        filters = {}

        if chart_type == "weekly":
            # Get last 7 days sales data
            today = timezone.now().date()
            weekly_data = []

            for i in range(7):
                date = today - timedelta(days=6 - i)
                day_sales = (
                    safe_model_query("Sale")
                    .filter(createDate__date=date, **filters)
                    .aggregate(total=Sum("totalAmount"))["total"]
                    or 0
                )

                weekly_data.append(
                    {
                        "day": date.strftime("%a"),
                        "date": date.strftime("%Y-%m-%d"),
                        "sales": float(day_sales),
                    }
                )

            return Response(
                {"success": True, "data": {"type": "weekly_trend", "data": weekly_data}}
            )

        elif chart_type == "category":
            # Get revenue by product category
            category_data = []

            # Get sales grouped by product category
            # This is a simplified version - you might need to join with products table
            sales_by_category = (
                safe_model_query("Sale")
                .filter(
                    **filters,
                    createDate__date__gte=timezone.now().date() - timedelta(days=30),
                )
                .values("items__product__category")
                .annotate(revenue=Sum("items__total"))
                .exclude(items__product__category__isnull=True)
            )

            # Mock data for now since we might not have category properly set up
            mock_categories = [
                {"category": "Kebab", "revenue": 8500},
                {"category": "Thai", "revenue": 12300},
                {"category": "Chinese", "revenue": 9800},
                {"category": "Drinks", "revenue": 6400},
                {"category": "Fast Food", "revenue": 11200},
            ]

            return Response(
                {
                    "success": True,
                    "data": {
                        "type": "category_revenue",
                        "data": mock_categories,  # Use mock data for now
                    },
                }
            )

        else:
            return Response(
                {
                    "success": False,
                    "error": "Invalid chart_type. Use: weekly, category",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recent_orders(request):
    """
    Get recent orders with details
    """
    try:
        # Get query parameters
        limit = int(request.GET.get("limit", 10))

        # No company/branch filters as models don't support them
        filters = {}

        # Get recent orders
        orders = (
            safe_model_query("Order").filter(**filters).order_by("-createdAt")[:limit]
        )

        orders_data = []
        for order in orders:
            # Calculate total items
            total_items = (
                safe_model_query("OrderItem")
                .filter(order=order)
                .aggregate(total=Sum("quantity"))["total"]
                or 0
            )

            orders_data.append(
                {
                    "id": f"ORD-{order.id}",
                    "table": order.name or "Takeaway",  # Using name field as table
                    "items": total_items,
                    "amount": float(order.totalAmount or 0),
                    "currency": "৳",
                    "status": order.status,
                    "created_at": (
                        order.createdAt.strftime("%Y-%m-%d %H:%M:%S")
                        if order.createdAt
                        else ""
                    ),
                    "customer_name": order.customer.name if order.customer else "Guest",
                }
            )

        return Response(
            {"success": True, "data": orders_data, "count": len(orders_data)}
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inventory_alerts(request):
    """
    Get low stock alerts and inventory status
    """
    try:
        # Get query parameters
        alert_type = request.GET.get(
            "alert_type", "low_stock"
        )  # low_stock, out_of_stock

        # No company/branch filters as models don't support them
        filters = {}

        if alert_type == "low_stock":
            # Get products with low stock (less than 10 units)
            low_stock_items = (
                safe_model_query("Stock")
                .filter(**filters, stock__lt=10, stock__gt=0)
                .select_related("product")[:20]
            )  # Limit to 20 items

            items_data = []
            for item in low_stock_items:
                items_data.append(
                    {
                        "id": item.id,
                        "name": (
                            item.product.product_name
                            if item.product
                            else f"Product {item.id}"
                        ),
                        "current": float(item.stock or 0),
                        "reorder_level": 10,  # Fixed threshold since model doesn't have this field
                        "unit": "pcs",  # Fixed since model doesn't have this field
                        "category": "General",  # Simplified since product category structure is complex
                        "last_updated": (
                            item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            if item.created_at
                            else None
                        ),
                    }
                )

            # If no real data, return mock data
            if not items_data:
                items_data = [
                    {
                        "name": "Chicken Breast",
                        "current": 12,
                        "unit": "kg",
                        "reorder_level": 50,
                        "category": "Meat",
                    },
                    {
                        "name": "Thai Basil",
                        "current": 5,
                        "unit": "bunches",
                        "reorder_level": 20,
                        "category": "Herbs",
                    },
                    {
                        "name": "Soy Sauce",
                        "current": 3,
                        "unit": "bottles",
                        "reorder_level": 15,
                        "category": "Condiments",
                    },
                    {
                        "name": "Basmati Rice",
                        "current": 8,
                        "unit": "kg",
                        "reorder_level": 30,
                        "category": "Grains",
                    },
                ]

        elif alert_type == "out_of_stock":
            # Get out of stock items
            out_of_stock_items = (
                safe_model_query("Stock")
                .filter(**filters, stock__lte=0)
                .select_related("product")[:20]
            )

            items_data = []
            for item in out_of_stock_items:
                items_data.append(
                    {
                        "id": item.id,
                        "name": (
                            item.product.product_name
                            if item.product
                            else f"Product {item.id}"
                        ),
                        "current": 0,
                        "unit": "pcs",
                        "category": "General",
                        "last_updated": (
                            item.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            if item.created_at
                            else None
                        ),
                    }
                )

        return Response(
            {
                "success": True,
                "data": items_data,
                "alert_type": alert_type,
                "count": len(items_data),
            }
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recent_activities(request):
    """
    Get recent activities across the system
    """
    try:
        # Get query parameters
        limit = int(request.GET.get("limit", 20))
        activity_type = request.GET.get(
            "type", "all"
        )  # all, sale, inventory, booking, etc.

        activities = []

        # Get recent sales
        if activity_type in ["all", "sale"]:
            filters_sales = {}

            recent_sales = (
                safe_model_query("Sale")
                .filter(**filters_sales)
                .order_by("-createDate")[:5]
            )
            for sale in recent_sales:
                activities.append(
                    {
                        "id": f"sale_{sale.id}",
                        "type": "sale",
                        "description": f"Sale completed: ৳{sale.totalAmount}",
                        "timestamp": (
                            sale.createDate.isoformat()
                            if sale.createDate
                            else timezone.now().isoformat()
                        ),
                        "user_name": (
                            sale.invoiceFrom.username if sale.invoiceFrom else "System"
                        ),
                        "branch_name": "Main Branch",  # Add branch logic later
                        "metadata": {
                            "amount": float(sale.totalAmount or 0),
                            "currency": "৳",
                            "order_id": sale.id,
                        },
                    }
                )

        # Get recent orders
        if activity_type in ["all", "order"]:
            filters_orders = {}

            recent_orders = (
                safe_model_query("Order")
                .filter(**filters_orders)
                .order_by("-createdAt")[:5]
            )
            for order in recent_orders:
                activities.append(
                    {
                        "id": f"order_{order.id}",
                        "type": "order",
                        "description": f"New order #{order.orderNumber or order.id} - {order.status}",
                        "timestamp": (
                            order.createdAt.isoformat()
                            if order.createdAt
                            else timezone.now().isoformat()
                        ),
                        "user_name": "Customer",
                        "branch_name": "Main Branch",
                        "metadata": {
                            "amount": float(order.totalAmount or 0),
                            "currency": "৳",
                            "status": order.status,
                            "table": order.name,
                        },
                    }
                )

        # Get recent inventory updates
        if activity_type in ["all", "inventory"]:
            filters_inventory = {}

            recent_stock_updates = (
                safe_model_query("Stock")
                .filter(**filters_inventory)
                .order_by("-updated_at")[:3]
            )
            for stock in recent_stock_updates:
                activities.append(
                    {
                        "id": f"stock_{stock.id}",
                        "type": "inventory",
                        "description": f'Stock updated: {stock.product.name if stock.product else "Unknown Product"}',
                        "timestamp": (
                            stock.updated_at.isoformat()
                            if stock.updated_at
                            else timezone.now().isoformat()
                        ),
                        "user_name": "System",
                        "branch_name": "Main Branch",
                        "metadata": {
                            "product": (
                                stock.product.name if stock.product else "Unknown"
                            ),
                            "quantity": float(stock.current_quantity or 0),
                            "unit": stock.unit,
                        },
                    }
                )

        # Sort activities by timestamp (most recent first)
        activities.sort(key=lambda x: x["timestamp"], reverse=True)

        # Limit results
        activities = activities[:limit]

        # If no real activities, return mock data
        if not activities:
            activities = [
                {
                    "id": "mock_1",
                    "type": "sale",
                    "description": "Sale completed: ৳245.50",
                    "timestamp": (timezone.now() - timedelta(minutes=5)).isoformat(),
                    "user_name": "John Doe",
                    "branch_name": "Main Branch",
                    "metadata": {"amount": 245.50, "currency": "৳"},
                },
                {
                    "id": "mock_2",
                    "type": "order",
                    "description": "New order #1234 - Preparing",
                    "timestamp": (timezone.now() - timedelta(minutes=15)).isoformat(),
                    "user_name": "Kitchen Staff",
                    "branch_name": "Main Branch",
                    "metadata": {"status": "preparing", "table": "T-12"},
                },
                {
                    "id": "mock_3",
                    "type": "inventory",
                    "description": "Low stock alert: Chicken Breast",
                    "timestamp": (timezone.now() - timedelta(hours=1)).isoformat(),
                    "user_name": "System",
                    "branch_name": "Main Branch",
                    "metadata": {"product": "Chicken Breast", "quantity": 12},
                },
            ]

        return Response(
            {
                "success": True,
                "data": activities,
                "count": len(activities),
                "activity_type": activity_type,
            }
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def financial_summary(request):
    """
    Get financial summary: sales, purchases, expenses, profit
    """
    try:
        # Get query parameters
        period = request.GET.get("period", "month")  # today, week, month, year

        # Calculate date filter
        today = timezone.now().date()
        if period == "today":
            start_date = today
            end_date = today
        elif period == "week":
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == "month":
            start_date = today - timedelta(days=30)
            end_date = today
        elif period == "year":
            start_date = today - timedelta(days=365)
            end_date = today
        else:
            start_date = today - timedelta(days=30)
            end_date = today

        # Different filters for different models due to different date field names
        sale_filters = {"createDate__date__range": [start_date, end_date]}
        other_filters = {"created_at__date__range": [start_date, end_date]}

        # Calculate financial metrics
        # Total Sales
        sales_data = (
            safe_model_query("Sale")
            .filter(**sale_filters)
            .aggregate(total_sales=Sum("totalAmount"), total_orders=Count("id"))
        )

        # Total Purchases
        purchase_data = (
            safe_model_query("Purchase")
            .filter(**other_filters)
            .aggregate(total_purchases=Sum("total_amount"))
        )

        # Total Expenses
        expense_data = (
            safe_model_query("Expense")
            .filter(**other_filters)
            .aggregate(total_expenses=Sum("amount"))
        )

        # Total Income (also uses created_at)
        income_data = (
            safe_model_query("Income")
            .filter(**other_filters)
            .aggregate(total_income=Sum("amount"))
        )

        total_sales = float(sales_data["total_sales"] or 0)
        total_purchases = float(purchase_data["total_purchases"] or 0)
        total_expenses = float(expense_data["total_expenses"] or 0)
        total_income = float(income_data["total_income"] or 0)

        # Calculate gross profit
        gross_profit = total_sales - total_purchases

        # Calculate net profit
        net_profit = total_sales + total_income - total_purchases - total_expenses

        summary = {
            "period": period,
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
            },
            "sales": {
                "amount": total_sales,
                "orders": sales_data["total_orders"] or 0,
                "currency": "৳",
            },
            "purchases": {"amount": total_purchases, "currency": "৳"},
            "expenses": {"amount": total_expenses, "currency": "৳"},
            "income": {"amount": total_income, "currency": "৳"},
            "profit": {
                "gross": gross_profit,
                "net": net_profit,
                "margin": (net_profit / total_sales * 100) if total_sales > 0 else 0,
                "currency": "৳",
            },
        }

        return Response({"success": True, "data": summary})

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def top_products(request):
    """
    Get top selling products and performance metrics
    """
    try:
        # Get query parameters
        period = request.GET.get("period", "month")
        limit = int(request.GET.get("limit", 10))

        # Calculate date filter
        today = timezone.now().date()
        if period == "today":
            start_date = today
        elif period == "week":
            start_date = today - timedelta(days=7)
        elif period == "month":
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=30)

        filters = {"order__createdAt__date__gte": start_date}

        # Get top products by quantity sold
        top_products = (
            safe_model_query("OrderItem")
            .filter(**filters)
            .values(
                "product__id",
                "name",  # Use name field from OrderItem
                "product__category",
                "price",
            )
            .annotate(
                total_quantity=Sum("quantity"),
                total_revenue=Sum("total"),
                order_count=Count("order", distinct=True),
            )
            .order_by("-total_quantity")[:limit]
        )

        products_data = []
        for product in top_products:
            products_data.append(
                {
                    "id": product["product__id"],
                    "name": product["name"] or "Unknown Product",
                    "category": product["product__category"] or "Uncategorized",
                    "price": float(product["price"] or 0),
                    "quantity_sold": product["total_quantity"],
                    "revenue": float(product["total_revenue"] or 0),
                    "order_count": product["order_count"],
                    "currency": "৳",
                }
            )

        # If no real data, return mock data
        if not products_data:
            products_data = [
                {
                    "name": "Chicken Biryani",
                    "category": "Main Course",
                    "price": 280,
                    "quantity_sold": 45,
                    "revenue": 12600,
                    "currency": "৳",
                },
                {
                    "name": "Thai Green Curry",
                    "category": "Thai",
                    "price": 320,
                    "quantity_sold": 38,
                    "revenue": 12160,
                    "currency": "৳",
                },
                {
                    "name": "Beef Kebab",
                    "category": "Kebab",
                    "price": 250,
                    "quantity_sold": 42,
                    "revenue": 10500,
                    "currency": "৳",
                },
                {
                    "name": "Mango Lassi",
                    "category": "Drinks",
                    "price": 80,
                    "quantity_sold": 67,
                    "revenue": 5360,
                    "currency": "৳",
                },
                {
                    "name": "Naan Bread",
                    "category": "Bread",
                    "price": 60,
                    "quantity_sold": 78,
                    "revenue": 4680,
                    "currency": "৳",
                },
            ]

        return Response(
            {
                "success": True,
                "data": products_data,
                "period": period,
                "count": len(products_data),
            }
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
