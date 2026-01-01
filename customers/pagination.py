from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomerPagination(PageNumberPagination):
    """
    Custom pagination class for Customer API with enhanced metadata
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        Return a paginated style Response object for the given output data
        with additional metadata for frontend components
        """
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.page_size,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "has_next": self.page.has_next(),
                "has_previous": self.page.has_previous(),
                "results": data,
            }
        )
