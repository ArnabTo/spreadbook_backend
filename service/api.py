from rest_framework.decorators import permission_classes
from .models import ServiceItem
from .serializers import ServiceItemSerializer, ProductServiceSerializer
from rest_framework import serializers, viewsets, permissions 



from common.drf_scoping import apply_company_branch_scope, is_unrestricted_user, get_company_ids_for_user
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


class ProductServicePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200


class ProductServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ProductServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ProductServicePagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category", "is_active", "quality_applicable"]
    search_fields = ["name", "code", "arabic_name"]
    ordering_fields = ["name", "code", "sales_price", "createdAt", "updatedAt"]
    ordering = ["name"]

    def get_queryset(self):
        from service.models import ProductService
        qs = ProductService.objects.select_related("company", "category").all()
        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="company_id",
            branch_id_field=None,
        )

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class ServiceItemViewSet(viewsets.ModelViewSet):
     queryset = ServiceItem.objects.all()
     serializer_class = ServiceItemSerializer
     lookup_field = 'slug'
     # # http_method_names= ['get']
     # def get_queryset(self):
     #      return Post.objects.all()