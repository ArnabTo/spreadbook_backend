from rest_framework import serializers
from django.contrib.auth.models import User
from sales.models import Sale, InvoiceItem
from order.models import Order, Item as OrderItem
from products.models import Product
from stock.models import Stock


class DashboardMetricsSerializer(serializers.Serializer):
    """Serializer for dashboard key metrics"""

    sales = serializers.DictField()
    orders = serializers.DictField()
    tables = serializers.DictField()
    avg_order_value = serializers.DictField()


class SalesAnalyticsSerializer(serializers.Serializer):
    """Serializer for sales analytics data"""

    type = serializers.CharField()
    data = serializers.ListField()


class RecentOrderSerializer(serializers.Serializer):
    """Serializer for recent orders"""

    id = serializers.CharField()
    table = serializers.CharField()
    items = serializers.IntegerField()
    amount = serializers.FloatField()
    currency = serializers.CharField(default="৳")
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    customer_name = serializers.CharField()


class InventoryAlertSerializer(serializers.Serializer):
    """Serializer for inventory alerts"""

    id = serializers.IntegerField(required=False)
    name = serializers.CharField()
    current = serializers.FloatField()
    reorder_level = serializers.FloatField(required=False)
    unit = serializers.CharField()
    category = serializers.CharField()
    last_updated = serializers.DateTimeField(required=False)


class ActivitySerializer(serializers.Serializer):
    """Serializer for recent activities"""

    id = serializers.CharField()
    type = serializers.CharField()
    description = serializers.CharField()
    timestamp = serializers.DateTimeField()
    user_name = serializers.CharField()
    branch_name = serializers.CharField()
    metadata = serializers.DictField()


class FinancialSummarySerializer(serializers.Serializer):
    """Serializer for financial summary"""

    period = serializers.CharField()
    date_range = serializers.DictField()
    sales = serializers.DictField()
    purchases = serializers.DictField()
    expenses = serializers.DictField()
    income = serializers.DictField()
    profit = serializers.DictField()


class TopProductSerializer(serializers.Serializer):
    """Serializer for top products"""

    id = serializers.IntegerField(required=False)
    name = serializers.CharField()
    category = serializers.CharField()
    price = serializers.FloatField()
    quantity_sold = serializers.IntegerField()
    revenue = serializers.FloatField()
    order_count = serializers.IntegerField(required=False)
    currency = serializers.CharField(default="৳")


class APIResponseSerializer(serializers.Serializer):
    """Generic API response serializer"""

    success = serializers.BooleanField()
    data = serializers.JSONField(required=False)
    error = serializers.CharField(required=False)
    count = serializers.IntegerField(required=False)
    filters_applied = serializers.DictField(required=False)
