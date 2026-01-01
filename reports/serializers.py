from rest_framework import serializers


class SalesOverviewSerializer(serializers.Serializer):
    """Serializer for sales overview report data"""

    period = serializers.CharField()
    date_range = serializers.DictField()
    summary = serializers.DictField()
    daily_breakdown = serializers.ListField()
    payment_methods = serializers.ListField()
    comparison = serializers.DictField(required=False, allow_null=True)


class ProductAnalysisSerializer(serializers.Serializer):
    """Serializer for product analysis report data"""

    period = serializers.CharField()
    date_range = serializers.DictField()
    top_products_by_quantity = serializers.ListField()
    top_products_by_revenue = serializers.ListField()
    category_performance = serializers.ListField()
    low_performing_products = serializers.ListField()
    profitable_products = serializers.ListField()
    summary = serializers.DictField()


class StaffPerformanceSerializer(serializers.Serializer):
    """Serializer for staff performance report data"""

    period = serializers.CharField()
    date_range = serializers.DictField()
    staff_performance = serializers.ListField()
    team_summary = serializers.DictField()
    rankings = serializers.DictField()
    productivity_metrics = serializers.ListField()
    departments = serializers.DictField()


class InventoryAnalysisSerializer(serializers.Serializer):
    """Serializer for inventory analysis report data"""

    period = serializers.CharField()
    date_range = serializers.DictField()
    consumption_details = serializers.ListField()
    summary = serializers.DictField()
    alerts = serializers.DictField()
    category_breakdown = serializers.ListField()
    supplier_performance = serializers.ListField()
    daily_consumption = serializers.ListField()


class FinancialAnalyticsSerializer(serializers.Serializer):
    """Serializer for financial analytics report data"""

    period = serializers.CharField()
    date_range = serializers.DictField()
    financial_summary = serializers.DictField()
    profitability = serializers.DictField()
    cost_breakdown = serializers.ListField()
    financial_ratios = serializers.DictField()
    cash_flow = serializers.DictField()
    monthly_breakdown = serializers.ListField()
    forecast = serializers.ListField()


class CustomerAnalyticsSerializer(serializers.Serializer):
    """Serializer for customer analytics report data"""

    period = serializers.CharField()
    date_range = serializers.DictField()
    customer_overview = serializers.DictField()
    customer_segments = serializers.ListField()
    top_customers = serializers.ListField()
    popular_items = serializers.ListField()
    peak_hours = serializers.ListField()
    satisfaction_metrics = serializers.DictField()
    retention_analysis = serializers.DictField()
    geographic_distribution = serializers.ListField()
    insights = serializers.DictField()


class ExportReportSerializer(serializers.Serializer):
    """Serializer for export report request"""

    report_type = serializers.ChoiceField(
        choices=[
            "sales_overview",
            "product_analysis",
            "staff_performance",
            "inventory_analysis",
            "financial_analytics",
            "customer_analytics",
        ]
    )
    format = serializers.ChoiceField(choices=["json", "csv", "pdf"], default="json")
    period = serializers.ChoiceField(
        choices=["today", "week", "month", "quarter", "year", "custom"], default="month"
    )


class ReportsSummarySerializer(serializers.Serializer):
    """Serializer for reports summary data"""

    available_reports = serializers.ListField()
    categories = serializers.DictField()
    total_reports = serializers.IntegerField()
    last_generated = serializers.CharField()
    supported_formats = serializers.ListField()
    supported_periods = serializers.ListField()
