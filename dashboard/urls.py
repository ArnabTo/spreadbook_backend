from django.urls import path, include
from . import views

urlpatterns = [
    # Full Dashboard Summary (single endpoint for all data)
    path("summary/", views.dashboard_full_summary, name="dashboard_full_summary"),
    # Dashboard Metrics
    path("metrics/", views.dashboard_metrics, name="dashboard_metrics"),
    # Sales Analytics
    path("analytics/sales/", views.sales_analytics, name="sales_analytics"),
    # Recent Data
    path("recent-orders/", views.recent_orders, name="recent_orders"),
    path("recent-activities/", views.recent_activities, name="recent_activities"),
    # Inventory Alerts
    path("inventory/alerts/", views.inventory_alerts, name="inventory_alerts"),
    # Financial Summary
    path("financial/summary/", views.financial_summary, name="financial_summary"),
    # Top Products
    path("products/top/", views.top_products, name="top_products"),
]
