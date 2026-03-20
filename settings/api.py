from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

try:
    from rest_framework_simplejwt.authentication import JWTAuthentication
    _JWT_AUTH = [JWTAuthentication]
except ImportError:
    _JWT_AUTH = []

from .models import SystemSettings
from .serializers import SystemSettingsSerializer
from common.drf_scoping import is_unrestricted_user


class SystemSettingsViewSet(viewsets.ModelViewSet):
    """
    CRUD for SystemSettings, scoped to the requesting user's company.

    List / Get:
      GET  /api/system-settings/              → company-level default (branch=null)
      GET  /api/system-settings/?branch=<id>  → branch override (auto-creates if absent)
      GET  /api/system-settings/<id>/

    Upsert helpers:
      POST   /api/system-settings/upsert/               → body: { company, branch?, ...fields }
      PATCH  /api/system-settings/<id>/

    Convenience:
      GET  /api/system-settings/for_company/?company=<id>
      GET  /api/system-settings/for_branch/?branch=<id>
    """

    serializer_class = SystemSettingsSerializer
    authentication_classes = _JWT_AUTH + \
        [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def _get_company_id(self):
        user = self.request.user
        return getattr(user, "companyId_id", None) or getattr(user, "companyId", None)

    def get_queryset(self):
        user = self.request.user
        qs = SystemSettings.objects.select_related("company", "branch")

        if is_unrestricted_user(user) or bool(getattr(user, "is_superuser", False)):
            company_id = self.request.query_params.get("company")
            if company_id:
                return qs.filter(company_id=company_id)
            return qs

        company_id = self._get_company_id()
        if company_id:
            return qs.filter(company_id=company_id)

        return SystemSettings.objects.none()

    def list(self, request, *args, **kwargs):
        """
        Return a single settings object for the given scope.
        Query params:
          - branch=<id>    branch override
          - company=<id>   explicit company (admins / unrestricted only)
        Auto-creates the record with defaults if it does not exist yet.
        """
        company_id = request.query_params.get(
            "company") or self._get_company_id()
        if not company_id:
            return Response({"detail": "No company context."}, status=status.HTTP_400_BAD_REQUEST)

        branch_id = request.query_params.get("branch") or None

        obj, _ = SystemSettings.objects.get_or_create(
            company_id=company_id,
            branch_id=branch_id,
        )
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(detail=False, methods=["post", "put", "patch"], url_path="upsert")
    def upsert(self, request):
        """
        Create or fully update a settings record identified by (company, branch).
        Body: { company, branch (optional), ...setting fields }
        """
        company_id = request.data.get("company") or self._get_company_id()
        if not company_id:
            return Response({"detail": "company is required."}, status=status.HTTP_400_BAD_REQUEST)

        branch_id = request.data.get("branch") or None

        obj, created = SystemSettings.objects.get_or_create(
            company_id=company_id,
            branch_id=branch_id,
        )
        partial = request.method in ("PATCH",)
        serializer = self.get_serializer(
            obj, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="for_company")
    def for_company(self, request):
        """
        GET /api/system-settings/for_company/?company=<id>
        Returns all settings records (company + branch overrides) for a company.
        """
        company_id = request.query_params.get(
            "company") or self._get_company_id()
        if not company_id:
            return Response({"detail": "company is required."}, status=status.HTTP_400_BAD_REQUEST)
        qs = SystemSettings.objects.filter(
            company_id=company_id).select_related("branch")
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="for_branch")
    def for_branch(self, request):
        """
        GET /api/system-settings/for_branch/?branch=<id>
        Returns branch-level settings (falling back to company default if not set).
        """
        branch_id = request.query_params.get("branch")
        if not branch_id:
            return Response({"detail": "branch is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Try branch-specific first
        obj = SystemSettings.objects.filter(branch_id=branch_id).first()
        if obj is None:
            # Fall back to company default
            company_id = self._get_company_id()
            if company_id:
                obj, _ = SystemSettings.objects.get_or_create(
                    company_id=company_id,
                    branch_id=None,
                )
            else:
                return Response({"detail": "No settings found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(self.get_serializer(obj).data)
