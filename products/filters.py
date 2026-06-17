from __future__ import annotations

import django_filters
from django.db.models import F, Q
from django.db.models.functions import Floor

from .models.product_model import Product


class ProductFilter(django_filters.FilterSet):
    """Custom filters for Product list.

    We keep `inventoryType` query param but make it accurate based on stock math,
    even if older rows have stale `inventoryType` values.

    Supported values (case-insensitive):
    - in stock | in_stock
    - low stock | low_stock
    - out of stock | out_of_stock
    - good | medium | low | critical
    """

    category = django_filters.CharFilter(field_name="category")
    status = django_filters.CharFilter(field_name="status")
    inventoryType = django_filters.CharFilter(method="filter_inventory_type")
    is_publish = django_filters.BooleanFilter(field_name="is_publish")
    supplier = django_filters.NumberFilter(field_name="supplier")
    unit = django_filters.NumberFilter(field_name="unit")

    def filter_inventory_type(self, queryset, name, value):
        if not value:
            return queryset

        normalized = str(value).strip().lower().replace("_", " ").replace("-", " ")
        normalized = " ".join(normalized.split())

        half_threshold = Floor(F("low_stock_threshold") * 0.5)

        # Truth source: stock quantity + threshold.
        # - out of stock: in_stock <= 0
        # - critical: 1..floor(threshold*0.5)
        # - low: (floor(threshold*0.5)+1)..threshold
        # - low stock: 1..threshold (includes critical)
        # - in stock: > threshold
        # - medium: (threshold+1)..(threshold*2)
        # - good: > (threshold*2)
        if normalized == "out of stock":
            return queryset.filter(Q(in_stock__lte=0) | Q(inventoryType="out of stock"))

        if normalized == "critical":
            return queryset.filter(Q(in_stock__gt=0) & Q(in_stock__lte=half_threshold))

        if normalized == "low":
            return queryset.filter(
                Q(in_stock__gt=half_threshold)
                & Q(in_stock__lte=F("low_stock_threshold"))
            )

        if normalized == "low stock":
            return queryset.filter(
                Q(in_stock__gt=0) & Q(in_stock__lte=F("low_stock_threshold"))
            )

        if normalized == "in stock":
            return queryset.filter(Q(in_stock__gt=F("low_stock_threshold")))

        if normalized == "medium":
            return queryset.filter(
                Q(in_stock__gt=F("low_stock_threshold"))
                & Q(in_stock__lte=F("low_stock_threshold") * 2)
            )

        if normalized == "good":
            return queryset.filter(Q(in_stock__gt=F("low_stock_threshold") * 2))

        # Fallback: raw filter
        return queryset.filter(**{name: value})

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "status",
            "inventoryType",
            "is_publish",
            "supplier",
            "unit",
        ]
