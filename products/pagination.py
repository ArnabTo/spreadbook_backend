from __future__ import annotations

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F
from collections import OrderedDict


class ProductPagination(PageNumberPagination):
    """Pagination tuned for large product catalogs.

    Backward-compatible: accepts both `page_size` (standard DRF) and `limit` (legacy).
    Includes summary stats in response.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200
    page_query_param = "page"

    def get_page_size(self, request):
        # Prefer explicit page_size
        page_size = super().get_page_size(request)
        if page_size:
            return page_size

        # Back-compat: allow `limit`
        raw_limit = request.query_params.get("limit")
        if not raw_limit:
            return self.page_size

        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return self.page_size

        if limit <= 0:
            return self.page_size

        return min(limit, self.max_page_size)

    def paginate_queryset(self, queryset, request, view=None):
        """Override to calculate summary stats from the full queryset."""
        # Calculate summary from full queryset BEFORE pagination
        self._summary = self._calculate_summary(queryset)
        return super().paginate_queryset(queryset, request, view)

    def _calculate_summary(self, queryset):
        """Calculate inventory summary stats from the queryset."""
        try:
            # Use database aggregation for efficiency
            stats = queryset.aggregate(
                total_value=Sum(F("in_stock") * F("price")),
                low_stock_count=Count(
                    "id",
                    filter=Q(in_stock__gt=0)
                    & Q(in_stock__lte=F("low_stock_threshold")),
                ),
                out_of_stock_count=Count("id", filter=Q(in_stock__lte=0)),
                in_stock_count=Count(
                    "id", filter=Q(in_stock__gt=F("low_stock_threshold"))
                ),
            )

            # Get unique categories count
            categories_count = (
                queryset.exclude(category__isnull=True)
                .exclude(category="")
                .values("category")
                .distinct()
                .count()
            )

            return {
                "total_value": float(stats["total_value"] or 0),
                "low_stock_count": stats["low_stock_count"] or 0,
                "out_of_stock_count": stats["out_of_stock_count"] or 0,
                "in_stock_count": stats["in_stock_count"] or 0,
                "categories_count": categories_count,
            }
        except Exception:
            return {
                "total_value": 0,
                "low_stock_count": 0,
                "out_of_stock_count": 0,
                "in_stock_count": 0,
                "categories_count": 0,
            }

    def get_paginated_response(self, data):
        """Include summary stats in the response."""
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("summary", getattr(self, "_summary", {})),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )
