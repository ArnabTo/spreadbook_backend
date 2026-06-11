from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import PermissionDenied

from accounts.models.account_models import Account
from accounts.models.bank_account_model import Bank
from accounts.serializers import (
    AccountSerializer,
    BankAccountSerializer,
)
from accounts.pagination import AccountPagination
from common.drf_scoping import is_unrestricted_user


class AccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer
    pagination_class = AccountPagination
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "name", "display_name", "bank_name", "email",
        "iban_no", "swift_code", "phone_number", "mobile_number",
    ]

    ordering_fields = [
        "name", "created_at", "updated_at", "opening_balance",
        "bank_name", "parent__name",
    ]
    ordering = ["-created_at"]

    def _resolve_company(self):
        user = self.request.user
        if getattr(user, "companyId", None):
            return user.companyId
        branches = user.branchAccess.select_related("company")
        company_ids = set(branches.values_list("company_id", flat=True))
        if len(company_ids) == 1 and branches.exists():
            return branches.first().company
        return None

    def _get_company_ids(self):
        user = self.request.user
        if is_unrestricted_user(user):
            return None
        ids = set()
        if getattr(user, "companyId_id", None):
            ids.add(user.companyId_id)
        ids.update(user.branchAccess.values_list("company_id", flat=True))
        return ids

    def get_queryset(self):
        queryset = Account.objects.select_related("parent", "country_ref", "state_ref", "company")
        company_ids = self._get_company_ids()
        if company_ids is not None:
            if not company_ids:
                return Account.objects.none()
            queryset = queryset.filter(company_id__in=company_ids)

        # Individual column filters
        id_filter = self.request.query_params.get("id", "").strip()
        name_filter = self.request.query_params.get("name", "").strip()
        mailing_name_filter = self.request.query_params.get("mailing_name", "").strip()
        parent_filter = self.request.query_params.get("parent", "").strip()
        mobile_filter = self.request.query_params.get("mobile_number", "").strip()

        if id_filter:
            queryset = queryset.filter(id__icontains=id_filter)
        if name_filter:
            queryset = queryset.filter(name__icontains=name_filter)
        if mailing_name_filter:
            queryset = queryset.filter(mailing_name__icontains=mailing_name_filter)
        if parent_filter:
            queryset = queryset.filter(parent__name__icontains=parent_filter)
        if mobile_filter:
            queryset = queryset.filter(mobile_number__icontains=mobile_filter)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return
        company = self._resolve_company()
        if not company:
            raise PermissionDenied("User is not associated with a company")
        serializer.save(company=company)

    def perform_update(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return
        company_ids = self._get_company_ids()
        if company_ids and str(serializer.instance.company_id) not in {str(c) for c in company_ids}:
            raise PermissionDenied("You do not have access to this account")
        serializer.save(company=serializer.instance.company)

    def perform_destroy(self, instance):
        user = self.request.user
        if not is_unrestricted_user(user):
            company_ids = self._get_company_ids()
            if company_ids and str(instance.company_id) not in {str(c) for c in company_ids}:
                raise PermissionDenied("You do not have access to this account")
        instance.delete()

    @action(detail=True, methods=["patch"])
    def toggle_status(self, request, pk=None):
        account = self.get_object()
        account.is_active = not account.is_active
        account.save(update_fields=["is_active", "updated_at"])
        return Response({
            "message": "Account status toggled",
            "id": str(account.id),
            "is_active": account.is_active,
        }, status=status.HTTP_200_OK)


# ── Legacy Bank viewset (preserved) ──

class BankAccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        return Bank.objects.filter(company_id=self.request.user.company_id)

