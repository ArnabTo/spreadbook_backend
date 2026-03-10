"""
API views for Supplier Ledger.

Endpoints:
  GET/POST  /api/supplier-ledger/ledgers/           — list (company-wise) + create manual
  GET/PATCH /api/supplier-ledger/ledgers/{id}/       — detail + update notes
  GET       /api/supplier-ledger/ledgers/{id}/detail/ — full detail with payments
  GET       /api/supplier-ledger/ledgers/summary/    — per-supplier totals

  GET/POST  /api/supplier-ledger/payments/           — list + record payment
  PATCH     /api/supplier-ledger/payments/{id}/      — cancel payment
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from company.models import Branch
from suppliers.models import Supplier
from .models import SupplierLedger, SupplierPayment
from .serializers import (
    SupplierLedgerListSerializer,
    SupplierLedgerDetailSerializer,
    SupplierPaymentSerializer,
    SupplierLedgerSummarySerializer,
)


def _is_unrestricted(user) -> bool:
    return (
        bool(getattr(user, "is_superuser", False))
        or getattr(user, "role", None) == "software_owner"
    )


def _resolve_company(user, request):
    """Resolve company from branch_id param, then user, then branch access."""
    branch_id = request.query_params.get(
        "branch_id") or request.data.get("branch_id")
    if branch_id:
        branch = Branch.objects.select_related(
            "company").filter(id=branch_id).first()
        if branch:
            return branch.company, branch

    if getattr(user, "companyId", None):
        return user.companyId, None

    if hasattr(user, "branchAccess") and user.branchAccess.exists():
        first_branch = user.branchAccess.select_related("company").first()
        return first_branch.company, first_branch

    return None, None


class SupplierLedgerViewSet(viewsets.ModelViewSet):
    """
    CRUD for SupplierLedger records.
    Automatically scoped to the authenticated user's company.
    Supports optional `branch_id` and `supplier` query params.
    Default scope: company-wide.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("retrieve",):
            return SupplierLedgerDetailSerializer
        return SupplierLedgerListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = SupplierLedger.objects.select_related(
            "supplier", "branch", "purchase_order"
        )

        # Scope by company
        company, branch = _resolve_company(user, self.request)
        if company is not None:
            qs = qs.filter(company=company)
        elif not _is_unrestricted(user):
            return qs.none()

        # Optional filters
        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        supplier_id = self.request.query_params.get("supplier")
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)

        # Filter by balance status
        status_filter = self.request.query_params.get("status")
        if status_filter == "paid":
            qs = qs.filter(balance__lte=0)
        elif status_filter == "unpaid":
            qs = qs.filter(balance__gt=0)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        company, branch = _resolve_company(user, self.request)
        if company is None:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot determine company for this user.")
        debit = serializer.validated_data.get("debit_amount", Decimal("0"))
        serializer.save(
            company=company,
            branch=branch,
            credit_amount=Decimal("0"),
            balance=debit,
        )

    @action(detail=True, methods=["get"], url_path="detail")
    def detail_view(self, request, pk=None):
        """Return full detail including all payments."""
        ledger = self.get_object()
        serializer = SupplierLedgerDetailSerializer(
            ledger, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        Per-supplier aggregated totals.
        Accepts same filters as list: branch_id, supplier.
        """
        qs = self.get_queryset()

        from django.db.models import Sum, Count
        rows = (
            qs.values("supplier", "supplier__name")
            .annotate(
                total_debit=Sum("debit_amount"),
                total_credit=Sum("credit_amount"),
                total_balance=Sum("balance"),
                ledger_count=Count("id"),
            )
            .order_by("supplier__name")
        )
        data = [
            {
                "supplier": row["supplier"],
                "supplier_name": row["supplier__name"],
                "total_debit": row["total_debit"] or Decimal("0"),
                "total_credit": row["total_credit"] or Decimal("0"),
                "total_balance": row["total_balance"] or Decimal("0"),
                "ledger_count": row["ledger_count"],
            }
            for row in rows
        ]
        serializer = SupplierLedgerSummarySerializer(data, many=True)
        return Response(serializer.data)


class SupplierPaymentViewSet(viewsets.ModelViewSet):
    """
    Record and manage payments against a SupplierLedger.
    POST to create a payment → ledger balance updates automatically.
    PATCH with is_cancelled=true to cancel a payment.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SupplierPaymentSerializer

    def get_queryset(self):
        user = self.request.user
        # Resolve company to scope payments
        company, _ = _resolve_company(user, self.request)

        qs = SupplierPayment.objects.select_related(
            "ledger", "ledger__supplier")

        if company is not None:
            qs = qs.filter(ledger__company=company)
        elif not _is_unrestricted(user):
            return qs.none()

        # Filter by ledger
        ledger_id = self.request.query_params.get("ledger")
        if ledger_id:
            qs = qs.filter(ledger_id=ledger_id)

        # Filter by supplier (across all ledgers for that supplier)
        supplier_id = self.request.query_params.get("supplier")
        if supplier_id:
            qs = qs.filter(ledger__supplier_id=supplier_id)

        # Filter by branch
        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            qs = qs.filter(ledger__branch_id=branch_id)

        return qs.order_by("-payment_date", "-created_at")

    def perform_create(self, serializer):
        with transaction.atomic():
            payment = serializer.save()
            # recalc is triggered in SupplierPayment.save()
            return payment

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Mark a payment as cancelled and recalc ledger balance."""
        payment = self.get_object()
        if payment.is_cancelled:
            return Response(
                {"detail": "Payment is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            payment.is_cancelled = True
            payment.save(update_fields=["is_cancelled", "updated_at"])
            payment.ledger.recalc()
        return Response(SupplierPaymentSerializer(payment).data)
