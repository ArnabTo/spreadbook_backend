with open('company/api.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix model imports
c = c.replace(
    "from .models import Company, Branch, CompanyCustomization, Warehouse",
    "from .models import Company, Branch, CompanyCustomization, Warehouse, Country, StateProvince"
)

# Fix serializer imports - add CountrySerializer, StateProvinceSerializer, WarehouseDetailSerializer
c = c.replace(
    "from .serializers import (\n    CompanySerializer,\n    CompanyListSerializer,\n    BranchSerializer,\n    CompanyCustomizationSerializer,\n    WarehouseSerializer,\n)",
    "from .serializers import (\n    CompanySerializer,\n    CompanyListSerializer,\n    BranchSerializer,\n    CompanyCustomizationSerializer,\n    WarehouseSerializer,\n    CountrySerializer,\n    StateProvinceSerializer,\n    WarehouseDetailSerializer,\n)"
)

# Ensure DjangoFilterBackend and PageNumberPagination imports exist
if 'from django_filters.rest_framework import DjangoFilterBackend' not in c:
    c = c.replace(
        'from rest_framework import serializers, viewsets, permissions, filters',
        'from rest_framework import serializers, viewsets, permissions, filters\nfrom django_filters.rest_framework import DjangoFilterBackend\nfrom rest_framework.pagination import PageNumberPagination'
    )

# Now add CountryViewSet, StateProvinceViewSet, WarehouseViewSet if not present
if 'class CountryViewSet' not in c:
    viewset_code = '''

class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.filter(is_active=True).order_by("name")
    serializer_class = CountrySerializer
    permission_classes = [permissions.IsAuthenticated]


class StateProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StateProvinceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StateProvince.objects.filter(is_active=True).select_related("country").order_by("name")
        country_id = self.request.query_params.get("country_id")
        if country_id:
            qs = qs.filter(country_id=country_id)
        return qs


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "city"]
    ordering_fields = ["name", "code", "city", "postedAt"]
    ordering = ["name"]

    def get_queryset(self):
        qs = Warehouse.objects.select_related("company", "country_ref", "state_ref").all()
        user = self.request.user
        from common.drf_scoping import is_unrestricted_user, get_company_ids_for_user
        if not is_unrestricted_user(user):
            company_ids = get_company_ids_for_user(user)
            if company_ids:
                qs = qs.filter(company_id__in=list(company_ids))
            else:
                return Warehouse.objects.none()
        return qs

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()
'''
    c += viewset_code

with open('company/api.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('API imports + viewsets FIXED')
