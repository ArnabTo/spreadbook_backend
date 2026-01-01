from __future__ import annotations

from rest_framework.pagination import PageNumberPagination


class ProductPagination(PageNumberPagination):
    """Pagination tuned for large product catalogs.

    Backward-compatible: accepts both `page_size` (standard DRF) and `limit` (legacy).
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
