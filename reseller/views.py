from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# from django_filters.rest_framework import DjangoFilterBackend  # Optional: install django-filter for advanced filtering
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Reseller, ResellerCommission
from .serializers import (
    ResellerSerializer,
    ResellerListSerializer,
    ResellerCreateUpdateSerializer,
    ResellerCommissionSerializer,
    ResellerStatsSerializer,
)


class ResellerListCreateView(generics.ListCreateAPIView):
    """
    GET: List all resellers with filtering and search
    POST: Create a new reseller
    """

    queryset = Reseller.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "companyName", "email", "phone"]
    ordering_fields = [
        "name",
        "companyName",
        "joinedDate",
        "totalRevenue",
        "commissionEarned",
    ]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ResellerCreateUpdateSerializer
        return ResellerListSerializer


class ResellerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific reseller
    PUT/PATCH: Update a reseller
    DELETE: Delete a reseller
    """

    queryset = Reseller.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ResellerCreateUpdateSerializer
        return ResellerSerializer


class ResellerStatsView(generics.RetrieveAPIView):
    """
    GET: Get detailed statistics for a reseller
    """

    queryset = Reseller.objects.all()
    serializer_class = ResellerStatsSerializer
    permission_classes = [IsAuthenticated]


class ResellerCommissionListCreateView(generics.ListCreateAPIView):
    """
    GET: List all commissions with filtering
    POST: Create a new commission record
    """

    queryset = ResellerCommission.objects.all()
    serializer_class = ResellerCommissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "commission_amount", "revenue_amount"]
    ordering = ["-created_at"]


class ResellerCommissionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific commission
    PUT/PATCH: Update a commission
    DELETE: Delete a commission
    """

    queryset = ResellerCommission.objects.all()
    serializer_class = ResellerCommissionSerializer
    permission_classes = [IsAuthenticated]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reseller_dashboard_stats(request):
    """
    GET: Get overall dashboard statistics for resellers
    """
    try:
        # Get query parameters for filtering
        status_filter = request.GET.get("status", "active")

        # Base queryset
        resellers = Reseller.objects.all()
        if status_filter != "all":
            resellers = resellers.filter(status=status_filter)

        # Calculate statistics
        total_resellers = resellers.count()
        active_resellers = resellers.filter(status="active").count()
        inactive_resellers = resellers.filter(status="inactive").count()
        suspended_resellers = resellers.filter(status="suspended").count()

        # Revenue statistics
        total_revenue = (
            resellers.aggregate(Sum("totalRevenue"))["totalRevenue__sum"] or 0
        )
        total_commission = (
            resellers.aggregate(Sum("commissionEarned"))["commissionEarned__sum"] or 0
        )

        # Commission statistics
        unpaid_commissions = (
            ResellerCommission.objects.filter(is_paid=False).aggregate(
                Sum("commission_amount")
            )["commission_amount__sum"]
            or 0
        )

        paid_commissions = (
            ResellerCommission.objects.filter(is_paid=True).aggregate(
                Sum("commission_amount")
            )["commission_amount__sum"]
            or 0
        )

        # Recent activity (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_commissions = ResellerCommission.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()

        # Top performing resellers
        top_resellers = resellers.order_by("-totalRevenue")[:5]
        top_resellers_data = ResellerListSerializer(top_resellers, many=True).data

        return Response(
            {
                "overview": {
                    "total_resellers": total_resellers,
                    "active_resellers": active_resellers,
                    "inactive_resellers": inactive_resellers,
                    "suspended_resellers": suspended_resellers,
                    "total_revenue": float(total_revenue),
                    "total_commission": float(total_commission),
                    "unpaid_commissions": float(unpaid_commissions),
                    "paid_commissions": float(paid_commissions),
                    "recent_commissions_30d": recent_commissions,
                },
                "top_resellers": top_resellers_data,
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_commission_paid(request, commission_id):
    """
    POST: Mark a commission as paid
    """
    try:
        commission = ResellerCommission.objects.get(id=commission_id)

        if commission.is_paid:
            return Response(
                {"error": "Commission is already marked as paid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        commission.is_paid = True
        commission.paid_date = timezone.now()
        commission.save()

        return Response(
            {
                "message": "Commission marked as paid successfully",
                "commission": ResellerCommissionSerializer(commission).data,
            }
        )

    except ResellerCommission.DoesNotExist:
        return Response(
            {"error": "Commission not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_reseller_status(request, reseller_id):
    """
    POST: Update reseller status (activate, deactivate, suspend)
    """
    try:
        reseller = Reseller.objects.get(id=reseller_id)
        new_status = request.data.get("status")

        if new_status not in ["active", "inactive", "suspended"]:
            return Response(
                {
                    "error": "Invalid status. Must be one of: active, inactive, suspended"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = reseller.status
        reseller.status = new_status
        reseller.save()

        return Response(
            {
                "message": f"Reseller status updated from {old_status} to {new_status}",
                "reseller": ResellerSerializer(reseller).data,
            }
        )

    except Reseller.DoesNotExist:
        return Response(
            {"error": "Reseller not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reseller_commissions_by_reseller(request, reseller_id):
    """
    GET: Get all commissions for a specific reseller
    """
    try:
        reseller = Reseller.objects.get(id=reseller_id)

        # Get query parameters
        is_paid = request.GET.get("is_paid")

        commissions = reseller.commissions.all()

        if is_paid is not None:
            is_paid_bool = is_paid.lower() == "true"
            commissions = commissions.filter(is_paid=is_paid_bool)

        commissions = commissions.order_by("-created_at")

        # Pagination could be added here if needed
        serializer = ResellerCommissionSerializer(commissions, many=True)

        return Response(
            {
                "reseller": ResellerListSerializer(reseller).data,
                "commissions": serializer.data,
                "total_commissions": commissions.count(),
            }
        )

    except Reseller.DoesNotExist:
        return Response(
            {"error": "Reseller not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
