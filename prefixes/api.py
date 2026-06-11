from rest_framework import viewsets, permissions
from .models import Prefix
from .serializers import PrefixListSerializer, PrefixDetailSerializer
from common.drf_scoping import is_unrestricted_user, get_company_ids_for_user


class PrefixViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return PrefixListSerializer
        return PrefixDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if is_unrestricted_user(user):
            queryset = Prefix.objects.all()
        else:
            company_ids = get_company_ids_for_user(user)
            queryset = Prefix.objects.filter(company_id__in=company_ids)

        # Per-column search filters
        search_prefix = self.request.query_params.get("search_prefix", "").strip()
        if search_prefix:
            queryset = queryset.filter(prefix__icontains=search_prefix)

        search_current_index = self.request.query_params.get("search_current_index", "").strip()
        if search_current_index and search_current_index.isdigit():
            queryset = queryset.filter(current_index=int(search_current_index))

        search_narration = self.request.query_params.get("search_narration", "").strip()
        if search_narration:
            queryset = queryset.filter(narration__icontains=search_narration)

        search_prefix_series = self.request.query_params.get("search_prefix_series", "").strip()
        if search_prefix_series:
            queryset = queryset.filter(prefix_series__icontains=search_prefix_series)

        search_select_mode = self.request.query_params.get("search_select_mode", "").strip()
        if search_select_mode:
            queryset = queryset.filter(extra_config__select_mode__icontains=search_select_mode)

        search_select_service = self.request.query_params.get("search_select_service", "").strip()
        if search_select_service:
            queryset = queryset.filter(extra_config__select_service__icontains=search_select_service)

        type_filter = self.request.query_params.get("type")
        if type_filter:
            queryset = queryset.filter(type=type_filter.strip())

        return queryset.select_related("financial_year").order_by("-created_at")
