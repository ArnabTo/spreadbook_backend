from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from common.drf_scoping import (
    apply_company_branch_scope,
    get_allowed_branch_ids_for_user,
    is_unrestricted_user,
)

from .models import Prescription
from .serializers import PrescriptionSerializer


class PrescriptionViewSet(viewsets.ModelViewSet):
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = Prescription.objects.all().select_related(
            "company",
            "branch",
            "customer",
            "created_by",
            "approved_by",
            "rejected_by",
        )
        return apply_company_branch_scope(
            request=self.request,
            queryset=qs,
            company_id_field="company_id",
            branch_id_field="branch_id",
        )

    def _resolve_company(self):
        user = self.request.user
        if getattr(user, "companyId", None):
            return user.companyId

        branches = user.branchAccess.select_related("company")
        company_ids = set(branches.values_list("company_id", flat=True))
        if len(company_ids) == 1 and branches.exists():
            return branches.first().company

        return None

    def perform_create(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save(created_by=user)
            return

        company = self._resolve_company()
        if not company:
            raise PermissionDenied("User is not associated with a company")

        branch = serializer.validated_data.get("branch")
        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if branch is not None:
            if str(branch.company_id) != str(company.id):
                raise PermissionDenied("Branch does not belong to your company")
            if (
                allowed_branch_ids is not None
                and str(branch.id) not in allowed_branch_ids
            ):
                raise PermissionDenied("You do not have access to this branch")

        serializer.save(company=company, created_by=user)

    def perform_update(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        serializer.save(company=serializer.instance.company)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        prescription = self.get_object()
        if prescription.status not in {"draft", "rejected"}:
            return Response(
                {"detail": "Prescription cannot be submitted from current status"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        prescription.mark_submitted()
        prescription.save(
            update_fields=["status", "submitted_at", "updateAt"]
        )  # Timestamp base field
        return Response(self.get_serializer(prescription).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        prescription = self.get_object()
        prescription.mark_approved(user=request.user)
        prescription.save(
            update_fields=["status", "approved_at", "approved_by", "updateAt"]
        )
        return Response(self.get_serializer(prescription).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        prescription = self.get_object()
        reason = request.data.get("reason")
        prescription.mark_rejected(user=request.user, reason=reason)
        prescription.save(
            update_fields=[
                "status",
                "rejected_at",
                "rejected_by",
                "rejection_reason",
                "updateAt",
            ]
        )
        return Response(self.get_serializer(prescription).data)
