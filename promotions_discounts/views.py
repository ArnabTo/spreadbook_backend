from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Promotion, PromotionUsage
from .serializers import (
    PromotionSerializer,
    PromotionUsageSerializer,
    PromotionValidationSerializer,
    PromotionStatsSerializer,
    BulkPromotionStatusSerializer,
)


class PromotionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing promotions
    """

    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["type", "status", "applicable_on", "company", "branch"]
    search_fields = ["name", "code", "description"]
    ordering_fields = ["created_at", "start_date", "end_date", "used_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Filter promotions by user's company"""
        queryset = Promotion.objects.all()

        company = getattr(self.request.user, "companyId", None) or getattr(
            self.request.user, "company", None
        )
        if company:
            queryset = queryset.filter(company=company)

        # Additional filters
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        type_filter = self.request.query_params.get("type")
        if type_filter:
            queryset = queryset.filter(type=type_filter)

        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        return queryset

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get promotion statistics"""
        queryset = self.get_queryset()

        stats = {
            "total_promotions": queryset.count(),
            "active_promotions": queryset.filter(status="active").count(),
            "scheduled_promotions": queryset.filter(status="scheduled").count(),
            "expired_promotions": queryset.filter(status="expired").count(),
            "total_redemptions": queryset.aggregate(Sum("used_count"))[
                "used_count__sum"
            ]
            or 0,
            "total_discount_given": PromotionUsage.objects.filter(
                promotion__company=(
                    getattr(request.user, "companyId", None)
                    or getattr(request.user, "company", None)
                )
            ).aggregate(Sum("discount_amount"))["discount_amount__sum"]
            or 0,
            "top_promotions": queryset.order_by("-used_count")[:5],
        }

        serializer = PromotionStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def toggle_status(self, request, pk=None):
        """Toggle promotion status between active and inactive"""
        promotion = self.get_object()

        if promotion.status == "active":
            promotion.status = "inactive"
        elif promotion.status == "inactive":
            promotion.status = "active"
        else:
            return Response(
                {"error": "Can only toggle between active and inactive status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        promotion.save()
        serializer = self.get_serializer(promotion)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_status_update(self, request):
        """Update status for multiple promotions"""
        serializer = BulkPromotionStatusSerializer(data=request.data)
        if serializer.is_valid():
            promotion_ids = serializer.validated_data["promotion_ids"]
            new_status = serializer.validated_data["status"]

            # Filter by user's company for security
            promotions = self.get_queryset().filter(id__in=promotion_ids)
            updated_count = promotions.update(status=new_status)

            return Response(
                {
                    "message": f"Updated {updated_count} promotions to {new_status}",
                    "updated_count": updated_count,
                }
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def validate_code(self, request):
        """Validate a promotion code and calculate discount"""
        serializer = PromotionValidationSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data["code"]
            order_value = serializer.validated_data["order_value"]

            try:
                promotion = Promotion.objects.get(
                    code=code, company=request.user.company
                )

                if not promotion.can_apply_to_order(order_value):
                    return Response(
                        {
                            "valid": False,
                            "message": "Promotion cannot be applied to this order",
                        }
                    )

                discount_amount = promotion.calculate_discount(order_value)

                return Response(
                    {
                        "valid": True,
                        "promotion": PromotionSerializer(promotion).data,
                        "discount_amount": discount_amount,
                        "final_amount": order_value - discount_amount,
                    }
                )

            except Promotion.DoesNotExist:
                return Response({"valid": False, "message": "Invalid promotion code"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def apply_to_order(self, request, pk=None):
        """Apply promotion to an order and track usage"""
        promotion = self.get_object()
        order_value = request.data.get("order_value", 0)
        customer_id = request.data.get("customer_id")
        order_id = request.data.get("order_id")

        if not promotion.can_apply_to_order(order_value):
            return Response(
                {"error": "Promotion cannot be applied to this order"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        discount_amount = promotion.calculate_discount(order_value)

        # Create usage record
        usage_data = {
            "promotion": promotion,
            "discount_amount": discount_amount,
            "order_value": order_value,
        }

        if customer_id:
            from customers.models import Customer

            try:
                customer = Customer.objects.get(id=customer_id)
                usage_data["customer"] = customer
            except Customer.DoesNotExist:
                pass

        if order_id:
            # You might want to add order model validation here
            usage_data["order_id"] = order_id

        PromotionUsage.objects.create(**usage_data)

        # Increment usage count
        promotion.used_count += 1
        promotion.save()

        return Response(
            {
                "success": True,
                "discount_amount": discount_amount,
                "final_amount": order_value - discount_amount,
                "promotion": PromotionSerializer(promotion).data,
            }
        )

    @action(detail=False, methods=["get"])
    def active_promotions(self, request):
        """Get all currently active promotions"""
        now = timezone.now()
        active_promotions = self.get_queryset().filter(
            status="active", start_date__lte=now, end_date__gte=now
        )

        serializer = self.get_serializer(active_promotions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def expiring_soon(self, request):
        """Get promotions expiring within 7 days"""
        end_date = timezone.now() + timezone.timedelta(days=7)
        expiring_promotions = self.get_queryset().filter(
            status="active", end_date__lte=end_date, end_date__gte=timezone.now()
        )

        serializer = self.get_serializer(expiring_promotions, many=True)
        return Response(serializer.data)


class PromotionUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing promotion usage history
    """

    serializer_class = PromotionUsageSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["promotion", "customer", "order"]
    ordering_fields = ["used_at", "discount_amount"]
    ordering = ["-used_at"]

    def get_queryset(self):
        """Filter usage by user's company"""
        queryset = PromotionUsage.objects.all()

        if self.request.user.company:
            queryset = queryset.filter(promotion__company=self.request.user.company)

        # Filter by promotion
        promotion_id = self.request.query_params.get("promotion")
        if promotion_id:
            queryset = queryset.filter(promotion_id=promotion_id)

        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(used_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(used_at__lte=end_date)

        return queryset

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get usage summary statistics"""
        queryset = self.get_queryset()

        summary = {
            "total_uses": queryset.count(),
            "total_discount_given": queryset.aggregate(Sum("discount_amount"))[
                "discount_amount__sum"
            ]
            or 0,
            "average_discount": queryset.aggregate(avg_discount=Avg("discount_amount"))[
                "avg_discount"
            ]
            or 0,
            "top_customers": queryset.values("customer__name")
            .annotate(usage_count=Count("id"), total_saved=Sum("discount_amount"))
            .order_by("-usage_count")[:10],
        }

        return Response(summary)
