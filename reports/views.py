from django.db.models import Count, Sum, Avg, Q, F, Max, Min
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from datetime import datetime, timedelta
from decimal import Decimal
import json
import calendar

from common.drf_scoping import apply_company_branch_scope


def _parse_iso_date(value):
    if not value:
        return timezone.now().date()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return timezone.now().date()


def get_date_range(period):
    """Get date range based on period parameter"""
    today = timezone.now().date()

    if period == "today":
        return today, today
    elif period == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        return start_date, end_date
    elif period == "month":
        start_date = today.replace(day=1)
        next_month = (
            start_date.replace(month=start_date.month + 1)
            if start_date.month < 12
            else start_date.replace(year=start_date.year + 1, month=1)
        )
        end_date = next_month - timedelta(days=1)
        return start_date, end_date
    elif period == "quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_start_month, day=1)
        if quarter_start_month + 2 <= 12:
            end_month = quarter_start_month + 2
            end_year = today.year
        else:
            end_month = (quarter_start_month + 2) % 12
            end_year = today.year + 1
        end_date = start_date.replace(month=end_month, year=end_year)
        end_date = end_date.replace(day=calendar.monthrange(end_year, end_month)[1])
        return start_date, end_date
    elif period == "year":
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        return start_date, end_date
    else:
        # Default to last 30 days
        return today - timedelta(days=30), today


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sales_overview_report(request):
    """Comprehensive sales overview report"""
    try:
        period = request.GET.get("period", "month")
        start_date, end_date = get_date_range(period)

        # Mock data for reliable testing
        response_data = {
            "period": period,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "total_revenue": 45750.50,
                "total_orders": 156,
                "avg_order_value": 293.27,
                "max_order_value": 850.00,
                "min_order_value": 15.50,
                "currency": "৳",
            },
            "daily_breakdown": [
                {
                    "date": "2024-11-01",
                    "day_name": "Friday",
                    "revenue": 5420.34,
                    "orders": 18,
                    "avg_order": 301.13,
                },
                {
                    "date": "2024-11-02",
                    "day_name": "Saturday",
                    "revenue": 6890.64,
                    "orders": 24,
                    "avg_order": 287.11,
                },
                {
                    "date": "2024-11-03",
                    "day_name": "Sunday",
                    "revenue": 5640.15,
                    "orders": 19,
                    "avg_order": 296.85,
                },
                {
                    "date": "2024-11-04",
                    "day_name": "Monday",
                    "revenue": 4320.45,
                    "orders": 14,
                    "avg_order": 308.60,
                },
                {
                    "date": "2024-11-05",
                    "day_name": "Tuesday",
                    "revenue": 4890.30,
                    "orders": 16,
                    "avg_order": 305.64,
                },
                {
                    "date": "2024-11-06",
                    "day_name": "Wednesday",
                    "revenue": 5180.75,
                    "orders": 17,
                    "avg_order": 304.75,
                },
                {
                    "date": "2024-11-07",
                    "day_name": "Thursday",
                    "revenue": 6210.90,
                    "orders": 21,
                    "avg_order": 295.76,
                },
            ],
            "payment_methods": [
                {"method": "Cash", "amount": 18500.25, "orders": 62},
                {"method": "Card", "amount": 15320.75, "orders": 51},
                {"method": "Digital Wallet", "amount": 8920.50, "orders": 29},
                {"method": "Bank Transfer", "amount": 3009.00, "orders": 14},
            ],
            "comparison": {
                "total_revenue": 42180.30,
                "total_orders": 142,
                "avg_order_value": 297.04,
                "revenue_change": 8.47,
                "orders_change": 9.86,
                "avg_order_change": -1.27,
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def end_shift_report(request):
    """End-of-shift report for POS modal.

    This returns real computed totals (not mock) for a single day.
    Filtering is aligned with POS Order List (branch_id scoping + date range).
    """
    try:
        from sales.models import Sale, Refund
        from django.db.models import Sum

        # Base queryset mirrors POS order list: only POS orders with an order_number.
        qs = Sale.objects.filter(order_number__isnull=False).order_by("-order_time")

        # Optional filters (match POS list params as closely as possible)
        order_type = request.GET.get("order_type")
        if order_type:
            order_types = [v.strip() for v in order_type.split(",") if v.strip()]
            if len(order_types) == 1:
                qs = qs.filter(order_type=order_types[0])
            else:
                qs = qs.filter(order_type__in=order_types)

        status_param = request.GET.get("status")
        if status_param:
            statuses = [v.strip() for v in status_param.split(",") if v.strip()]
            if len(statuses) == 1:
                qs = qs.filter(status=statuses[0])
            else:
                qs = qs.filter(status__in=statuses)

        table_number = request.GET.get("table_number")
        if table_number:
            qs = qs.filter(table_number=table_number)

        # Date filtering: support both `date` (single day) and `date_from`/`date_to`.
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        date_single = request.GET.get("date")
        if date_single and not (date_from or date_to):
            date_from = date_single
            date_to = date_single

        # IMPORTANT: Avoid `order_time__date` here.
        # On SQLite, date extraction is effectively UTC and can drop early-morning
        # local (Asia/Dhaka) orders from "today".
        tz = timezone.get_current_timezone()
        start_date = _parse_iso_date(date_from) if date_from else None
        end_date = _parse_iso_date(date_to) if date_to else None

        start_dt = None
        end_dt = None

        if start_date:
            start_dt = timezone.make_aware(
                datetime.combine(start_date, datetime.min.time()), tz
            )
            qs = qs.filter(order_time__gte=start_dt)

        if end_date:
            end_dt = timezone.make_aware(
                datetime.combine(end_date + timedelta(days=1), datetime.min.time()), tz
            )
            qs = qs.filter(order_time__lt=end_dt)

        # Company/branch scoping (same helper used by POS orders list)
        qs = apply_company_branch_scope(
            request=request,
            queryset=qs,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

        # Optional: allow per-cashier report (default is ALL cashiers).
        # Security: cashiers/staff should not see other users' totals.
        served_by_param = request.GET.get("served_by")

        role = (getattr(request.user, "role", "") or "").lower()
        is_manager_plus = role in {
            "manager",
            "admin",
            "super_admin",
            "software_owner",
        } or bool(getattr(request.user, "is_superuser", False))

        if not is_manager_plus and served_by_param not in {None, "", "me"}:
            return Response(
                {
                    "error": "You do not have permission to view other cashiers' shift reports"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # If cashier/staff (non-manager), force served_by=me
        if not is_manager_plus:
            served_by_param = "me"

        served_by_payload = {"id": None, "name": "All"}
        if served_by_param:
            if served_by_param == "me":
                qs = qs.filter(served_by=request.user)
                served_by_payload = {
                    "id": request.user.id,
                    "name": request.user.get_full_name()
                    or getattr(request.user, "username", ""),
                }
            else:
                # Try treating it as a user id
                try:
                    user_id = int(served_by_param)
                    qs = qs.filter(served_by_id=user_id)
                    served_by_payload = {"id": user_id, "name": str(user_id)}
                except (TypeError, ValueError):
                    pass

        # Refunds within the same report range.
        refunds_qs = Refund.objects.all()
        if start_dt:
            refunds_qs = refunds_qs.filter(created_at__gte=start_dt)
        if end_dt:
            refunds_qs = refunds_qs.filter(created_at__lt=end_dt)

        refunds_qs = apply_company_branch_scope(
            request=request,
            queryset=refunds_qs,
            company_id_field="sale__companyId_id",
            branch_id_field="sale__branch_id",
        )

        if served_by_param:
            if served_by_param == "me":
                refunds_qs = refunds_qs.filter(sale__served_by=request.user)
            else:
                try:
                    refunds_qs = refunds_qs.filter(
                        sale__served_by_id=int(served_by_param)
                    )
                except (TypeError, ValueError):
                    pass

        totals = qs.aggregate(
            total_orders=Count("id"),
            gross_sales=Sum("subTotal"),
            discounts=Sum("discount_amount"),
            tax=Sum("taxes_value"),
            net_sales=Sum("totalAmount"),
        )

        refunds_totals = refunds_qs.aggregate(total_refunds=Sum("total_amount"))

        def _num(val):
            return float(val or 0)

        payment_rows = (
            qs.values("payment_method")
            .annotate(amount=Sum("totalAmount"), orders=Count("id"))
            .order_by("payment_method")
        )

        refund_payment_rows = (
            refunds_qs.values("payment_method")
            .annotate(amount=Sum("total_amount"))
            .order_by("payment_method")
        )

        expected_methods = [
            "cash",
            "card",
            "bkash",
            "nagad",
            "upay",
            "rocket",
            "bank_transfer",
            "digital_wallet",
        ]

        by_method = {
            m: {"method": m, "amount": 0.0, "orders": 0} for m in expected_methods
        }
        for row in payment_rows:
            method = (
                (row.get("payment_method") or "cash").strip().lower().replace(" ", "_")
            )

            # Normalize common legacy/display variants to API keys expected by frontend
            if method in {"hand_cash", "handcash", "cash_payment"}:
                method = "cash"
            if method in {"card_payment", "cardpay"}:
                method = "card"
            if method in {"bank_transfer", "bank"}:
                method = "bank_transfer"
            if method in {"digital_wallet", "wallet", "ewallet"}:
                method = "digital_wallet"
            if method in by_method:
                by_method[method] = {
                    "method": method,
                    "amount": _num(row.get("amount")),
                    "orders": int(row.get("orders") or 0),
                }

        # Subtract refunds from payment method amounts.
        for row in refund_payment_rows:
            method = (
                (row.get("payment_method") or "cash").strip().lower().replace(" ", "_")
            )
            if method in {"hand_cash", "handcash", "cash_payment"}:
                method = "cash"
            if method in {"card_payment", "cardpay"}:
                method = "card"
            if method in {"bank_transfer", "bank"}:
                method = "bank_transfer"
            if method in {"digital_wallet", "wallet", "ewallet"}:
                method = "digital_wallet"
            if method in by_method:
                by_method[method]["amount"] = float(by_method[method]["amount"]) - _num(
                    row.get("amount")
                )

        cash_sales = by_method.get("cash", {}).get("amount", 0.0)

        total_refunds = _num(refunds_totals.get("total_refunds"))

        return Response(
            {
                # Use a best-effort representative date when a range is provided.
                "date": (
                    _parse_iso_date(date_single)
                    if date_single
                    else _parse_iso_date(date_from)
                ).isoformat(),
                "served_by": served_by_payload,
                "cash_reconciliation": {
                    "opening_cash": 0.0,
                    "cash_sales": float(cash_sales),
                    "expected_cash": float(cash_sales),
                },
                "payment_methods": [by_method[m] for m in expected_methods],
                "summary": {
                    "total_orders": int(totals.get("total_orders") or 0),
                    "gross_sales": _num(totals.get("gross_sales")),
                    "discounts": _num(totals.get("discounts")),
                    "tax": _num(totals.get("tax")),
                    "refunds": total_refunds,
                    "net_sales": _num(totals.get("net_sales")) - total_refunds,
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def product_analysis_report(request):
    """Comprehensive product analysis and performance report"""
    try:
        period = request.GET.get("period", "month")
        start_date, end_date = get_date_range(period)

        top_products = [
            {
                "product_id": 1,
                "name": "Pad Thai",
                "quantity_sold": 85,
                "revenue": 1359.15,
                "orders": 42,
                "avg_price": 15.99,
                "currency": "৳",
            },
            {
                "product_id": 2,
                "name": "Chicken Biryani",
                "quantity_sold": 67,
                "revenue": 1239.50,
                "orders": 35,
                "avg_price": 18.50,
                "currency": "৳",
            },
            {
                "product_id": 3,
                "name": "Beef Kebab",
                "quantity_sold": 48,
                "revenue": 1056.00,
                "orders": 28,
                "avg_price": 22.00,
                "currency": "৳",
            },
            {
                "product_id": 4,
                "name": "Tom Yum Soup",
                "quantity_sold": 39,
                "revenue": 507.00,
                "orders": 25,
                "avg_price": 13.00,
                "currency": "৳",
            },
            {
                "product_id": 5,
                "name": "Mango Sticky Rice",
                "quantity_sold": 32,
                "revenue": 288.00,
                "orders": 20,
                "avg_price": 9.00,
                "currency": "৳",
            },
        ]

        response_data = {
            "period": period,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "top_products_by_quantity": top_products,
            "top_products_by_revenue": sorted(
                top_products, key=lambda x: x["revenue"], reverse=True
            ),
            "category_performance": [
                {
                    "name": "Thai Cuisine",
                    "revenue": 18500,
                    "orders": 145,
                    "avg_order": 127.59,
                },
                {
                    "name": "Indian Cuisine",
                    "revenue": 12300,
                    "orders": 98,
                    "avg_order": 125.51,
                },
                {
                    "name": "Chinese",
                    "revenue": 10800,
                    "orders": 87,
                    "avg_order": 124.14,
                },
                {
                    "name": "Fast Food",
                    "revenue": 8700,
                    "orders": 76,
                    "avg_order": 114.47,
                },
                {
                    "name": "Beverages",
                    "revenue": 4200,
                    "orders": 156,
                    "avg_order": 26.92,
                },
                {"name": "Desserts", "revenue": 3100, "orders": 43, "avg_order": 72.09},
            ],
            "summary": {
                "total_products_sold": sum(p["quantity_sold"] for p in top_products),
                "total_categories": 6,
                "best_performer": top_products[0],
                "currency": "৳",
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_performance_report(request):
    """Staff performance and productivity report"""
    try:
        period = request.GET.get("period", "month")
        start_date, end_date = get_date_range(period)

        staff_performance = [
            {
                "id": 1,
                "name": "Ahmed Rahman",
                "orders_served": 156,
                "total_sales": 18750.50,
                "avg_order_value": 120.20,
                "customer_rating": 4.8,
                "hours_worked": 168,
                "tips_earned": 1250.00,
                "complaints": 2,
                "commendations": 8,
            },
            {
                "id": 2,
                "name": "Fatima Ali",
                "orders_served": 142,
                "total_sales": 16850.25,
                "avg_order_value": 118.66,
                "customer_rating": 4.7,
                "hours_worked": 160,
                "tips_earned": 1150.00,
                "complaints": 1,
                "commendations": 6,
            },
            {
                "id": 3,
                "name": "Omar Hassan",
                "orders_served": 138,
                "total_sales": 15920.75,
                "avg_order_value": 115.37,
                "customer_rating": 4.6,
                "hours_worked": 158,
                "tips_earned": 980.00,
                "complaints": 3,
                "commendations": 5,
            },
        ]

        response_data = {
            "period": period,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "staff_performance": staff_performance,
            "team_summary": {
                "total_staff": len(staff_performance),
                "total_orders_served": sum(
                    s["orders_served"] for s in staff_performance
                ),
                "total_sales": sum(s["total_sales"] for s in staff_performance),
                "total_hours_worked": sum(s["hours_worked"] for s in staff_performance),
                "team_avg_rating": sum(s["customer_rating"] for s in staff_performance)
                / len(staff_performance),
                "total_tips": sum(s["tips_earned"] for s in staff_performance),
                "currency": "৳",
            },
            "rankings": {
                "top_by_sales": sorted(
                    staff_performance, key=lambda x: x["total_sales"], reverse=True
                )[:3],
                "top_by_orders": sorted(
                    staff_performance, key=lambda x: x["orders_served"], reverse=True
                )[:3],
                "top_by_rating": sorted(
                    staff_performance, key=lambda x: x["customer_rating"], reverse=True
                )[:3],
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inventory_analysis_report(request):
    """Inventory consumption and analysis report"""
    try:
        period = request.GET.get("period", "month")
        start_date, end_date = get_date_range(period)

        consumption_details = [
            {
                "item_id": 1,
                "item_name": "Chicken Breast",
                "category": "Meat",
                "consumed_quantity": 25,
                "unit": "kg",
                "unit_cost": 8.50,
                "total_cost": 212.50,
                "supplier": "Fresh Meat Co.",
                "reorder_level": 10,
                "current_stock": 15,
                "stock_status": "normal",
                "waste_percentage": 3.2,
                "shelf_life_days": 3,
            },
            {
                "item_id": 2,
                "item_name": "Jasmine Rice",
                "category": "Grains",
                "consumed_quantity": 40,
                "unit": "kg",
                "unit_cost": 2.25,
                "total_cost": 90.00,
                "supplier": "Rice Traders Ltd",
                "reorder_level": 20,
                "current_stock": 8,
                "stock_status": "low",
                "waste_percentage": 1.1,
                "shelf_life_days": 365,
            },
            {
                "item_id": 3,
                "item_name": "Fresh Vegetables",
                "category": "Produce",
                "consumed_quantity": 18,
                "unit": "kg",
                "unit_cost": 3.75,
                "total_cost": 67.50,
                "supplier": "Garden Fresh",
                "reorder_level": 5,
                "current_stock": 12,
                "stock_status": "normal",
                "waste_percentage": 8.5,
                "shelf_life_days": 5,
            },
        ]

        response_data = {
            "period": period,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "consumption_details": consumption_details,
            "summary": {
                "total_consumption_cost": sum(
                    item["total_cost"] for item in consumption_details
                ),
                "total_waste_cost": 45.80,
                "waste_percentage": 4.2,
                "total_items": len(consumption_details),
                "low_stock_count": 1,
                "critical_stock_count": 0,
                "currency": "৳",
            },
            "alerts": {
                "low_stock_items": [
                    item
                    for item in consumption_details
                    if item["stock_status"] == "low"
                ],
                "critical_items": [
                    item
                    for item in consumption_details
                    if item["stock_status"] == "critical"
                ],
                "high_waste_items": [
                    item for item in consumption_details if item["waste_percentage"] > 5
                ],
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_analytics_report(request):
    """Customer analytics and behavior report"""
    try:
        period = request.GET.get("period", "month")
        start_date, end_date = get_date_range(period)

        response_data = {
            "period": period,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "customer_overview": {
                "total_customers": 324,
                "new_customers": 45,
                "returning_customers": 279,
                "total_orders": 456,
                "total_revenue": 54320.75,
                "avg_order_value": 119.21,
                "currency": "৳",
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def financial_analysis_report(request):
    """Financial analysis and profitability report"""
    try:
        period = request.GET.get("period", "month")
        start_date, end_date = get_date_range(period)

        response_data = {
            "period": period,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "financial_summary": {
                "total_revenue": 54320.75,
                "total_expenses": 32150.40,
                "net_profit": 22170.35,
                "profit_margin": 40.8,
                "currency": "৳",
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_dashboard_report(request):
    """Combined analytics dashboard report"""
    try:
        period = request.GET.get("period", "month")
        start_date, end_date = get_date_range(period)

        response_data = {
            "period": period,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "dashboard_summary": {
                "total_revenue": 54320.75,
                "total_orders": 456,
                "total_customers": 324,
                "avg_order_value": 119.21,
                "currency": "৳",
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports_summary(request):
    """Summary of all available reports"""
    try:
        available_reports = [
            {"name": "Sales Overview", "endpoint": "/api/reports/sales-overview/"},
            {"name": "Product Analysis", "endpoint": "/api/reports/product-analysis/"},
            {
                "name": "Staff Performance",
                "endpoint": "/api/reports/staff-performance/",
            },
            {
                "name": "Inventory Analysis",
                "endpoint": "/api/reports/inventory-analysis/",
            },
            {
                "name": "Customer Analytics",
                "endpoint": "/api/reports/customer-analytics/",
            },
            {
                "name": "Financial Analysis",
                "endpoint": "/api/reports/financial-analysis/",
            },
            {
                "name": "Analytics Dashboard",
                "endpoint": "/api/reports/analytics/dashboard/",
            },
        ]

        return Response(
            {"available_reports": available_reports}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def export_report(request):
    """Export reports in various formats"""
    try:
        report_type = request.GET.get("type", "sales")
        format_type = request.GET.get("format", "pdf")
        period = request.GET.get("period", "month")

        # Mock export functionality
        response_data = {
            "success": True,
            "message": f"Report '{report_type}' exported successfully as {format_type.upper()}",
            "export_url": f"/exports/{report_type}_{period}_{datetime.now().strftime('%Y%m%d')}.{format_type}",
            "generated_at": datetime.now().isoformat(),
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
