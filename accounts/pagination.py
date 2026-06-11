from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class AccountPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "page_size": self.page.paginator.per_page,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
            "has_next": self.page.has_next(),
            "has_previous": self.page.has_previous(),
        })
