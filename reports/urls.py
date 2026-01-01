from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # Sales Reports
    path("sales-overview/", views.sales_overview_report, name="sales_overview_report"),
    path("end-shift/", views.end_shift_report, name="end_shift_report"),
    # Product Reports
    path(
        "product-analysis/",
        views.product_analysis_report,
        name="product_analysis_report",
    ),
    # Staff Reports
    path(
        "staff-performance/",
        views.staff_performance_report,
        name="staff_performance_report",
    ),
    # Inventory Reports
    path(
        "inventory-analysis/",
        views.inventory_analysis_report,
        name="inventory_analysis_report",
    ),
    # Financial Reports
    path(
        "financial-analysis/",
        views.financial_analysis_report,
        name="financial_analysis_report",
    ),
    # Customer Reports
    path(
        "customer-analytics/",
        views.customer_analytics_report,
        name="customer_analytics_report",
    ),
    # Export and Utility
    path("export/", views.export_report, name="export_report"),
    path("summary/", views.reports_summary, name="reports_summary"),
]
