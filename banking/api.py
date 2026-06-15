from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.drf_scoping import (
    apply_company_branch_scope,
    get_company_ids_for_user,
    is_unrestricted_user,
)
from company.models import Company

from .models import BankAccount
from .serializers import BankAccountSerializer


class BankAccountPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BankAccountViewSet(viewsets.ModelViewSet):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = BankAccountPageNumberPagination

    def get_queryset(self):
        qs = BankAccount.objects.all().order_by("name")
        return apply_company_branch_scope(
            request=self.request, queryset=qs,
            company_id_field="companyId_id", branch_id_field=None,
        )

    def perform_create(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            company = serializer.validated_data.get("companyId")
        else:
            ids = list(get_company_ids_for_user(user))
            company = Company.objects.filter(id__in=ids).first() if ids else None
        serializer.save(companyId=company, user=user)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=["get"], url_path="active")
    def active_list(self, request):
        qs = self.get_queryset().filter(is_active=True)
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)
