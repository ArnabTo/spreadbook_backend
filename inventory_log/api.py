from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q
from django.utils.timezone import now, make_aware
from datetime import datetime, timedelta, date
import calendar

from .models import InventoryLog
from .serializers import InventoryLogSerializer


class InventoryLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InventoryLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = InventoryLog.objects.all()

        # Company / branch scoping
        company_id = self.request.query_params.get("companyId")
        branch_id = self.request.query_params.get("branch")
        if company_id:
            qs = qs.filter(companyId=company_id)
        if branch_id:
            qs = qs.filter(branch=branch_id)

        # Category filter
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)

        # Log type filter
        log_type = self.request.query_params.get("log_type")
        if log_type:
            qs = qs.filter(log_type=log_type)

        # Date-range filter helpers
        period = self.request.query_params.get("period")  # today | month | year
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        today = date.today()

        if period == "today":
            qs = qs.filter(created_at__date=today)
        elif period == "month":
            qs = qs.filter(
                created_at__year=today.year,
                created_at__month=today.month,
            )
        elif period == "year":
            qs = qs.filter(created_at__year=today.year)
        elif date_from or date_to:
            if date_from:
                qs = qs.filter(created_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(created_at__date__lte=date_to)

        return qs

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        Returns:
          - total_in  (amount)
          - total_out (amount)
          - net       (total_in - total_out)
          - by_category: { purchase: {in, out}, sale: {in, out}, expense: {in, out}, ... }
        """
        qs = self.get_queryset()

        agg = qs.aggregate(
            total_in=Sum("amount", filter=Q(log_type="in")),
            total_out=Sum("amount", filter=Q(log_type="out")),
        )
        total_in = float(agg["total_in"] or 0)
        total_out = float(agg["total_out"] or 0)

        # Per-category breakdown
        category_labels = dict(InventoryLog._meta.get_field("category").choices)
        by_category = {}
        for cat_key in category_labels:
            cat_agg = qs.filter(category=cat_key).aggregate(
                in_amount=Sum("amount", filter=Q(log_type="in")),
                out_amount=Sum("amount", filter=Q(log_type="out")),
                in_qty=Sum("quantity", filter=Q(log_type="in")),
                out_qty=Sum("quantity", filter=Q(log_type="out")),
            )
            by_category[cat_key] = {
                "label": category_labels[cat_key],
                "in_amount": float(cat_agg["in_amount"] or 0),
                "out_amount": float(cat_agg["out_amount"] or 0),
                "in_qty": float(cat_agg["in_qty"] or 0),
                "out_qty": float(cat_agg["out_qty"] or 0),
            }

        return Response(
            {
                "total_in": total_in,
                "total_out": total_out,
                "net": total_in - total_out,
                "by_category": by_category,
            }
        )
