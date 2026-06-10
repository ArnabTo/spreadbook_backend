from rest_framework import viewsets, permissions
from .models import FinancialYear
from .serializers import FinancialYearSerializer
from common.drf_scoping import is_unrestricted_user, get_company_ids_for_user


class FinancialYearViewSet(viewsets.ModelViewSet):
    serializer_class = FinancialYearSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if is_unrestricted_user(user):
            queryset = FinancialYear.objects.all()
        else:
            company_ids = get_company_ids_for_user(user)
            queryset = FinancialYear.objects.filter(company_id__in=company_ids)

        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name.strip())

        return queryset.select_related("company").order_by("-from_date")
