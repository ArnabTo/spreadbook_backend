from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import AccountGroup, AccountGroupParent
from .serializers import (
    AccountGroupParentSerializer,
    AccountGroupListSerializer,
    AccountGroupDetailSerializer,
)
from common.drf_scoping import is_unrestricted_user, get_company_ids_for_user

PARENT_SEED_DATA = [
    "Assets",
    "Bank",
    "Capital Account",
    "Cash",
    "Creditor",
    "Current Assets",
    "Current Liability",
    "Debtor",
    "Direct Expense",
    "Direct Income",
    "Duties And Taxes",
    "Employee Account",
    "Expense",
    "Fixed Assets",
    "Income",
    "Indirect Expense",
    "Indirect Income",
    "Liabilities",
    "Manpower Group",
    "Purchase",
    "Salary Payable A/C",
    "Sales",
    "Sales Advance Group",
]


class AccountGroupParentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AccountGroupParent.objects.filter(is_active=True)
    serializer_class = AccountGroupParentSerializer
    permission_classes = [permissions.IsAuthenticated]


class AccountGroupViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return AccountGroupListSerializer
        return AccountGroupDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if is_unrestricted_user(user):
            queryset = AccountGroup.objects.all()
        else:
            company_ids = get_company_ids_for_user(user)
            queryset = AccountGroup.objects.filter(company_id__in=company_ids)

        name = self.request.query_params.get("name")
        account_code = self.request.query_params.get("account_code")

        if name:
            queryset = queryset.filter(name__icontains=name.strip())
        if account_code:
            queryset = queryset.filter(account_code__icontains=account_code.strip())

        return queryset.select_related("parent").order_by("name")

    @action(detail=False, methods=["post"], url_path="seed")
    def seed_parents(self, request):
        created = 0
        with transaction.atomic():
            for entry in PARENT_SEED_DATA:
                _, was_created = AccountGroupParent.objects.get_or_create(name=entry)
                if was_created:
                    created += 1

        return Response(
            {
                "success": True,
                "message": "Account group parent data seeded successfully",
                "created": created,
            },
            status=status.HTTP_200_OK,
        )
