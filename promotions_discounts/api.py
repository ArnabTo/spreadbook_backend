"""
API endpoints for Promotions & Discounts module
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .models import Promotion, PromotionUsage
from .serializers import PromotionSerializer, PromotionUsageSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_promotions(request):
    """Get all promotions for the user's company or created by user"""
    try:
        # Filter by company if available, otherwise by creator
        if hasattr(request.user, "company") and request.user.company:
            promotions = Promotion.objects.filter(company=request.user.company)
        else:
            promotions = Promotion.objects.filter(created_by=request.user)

        # Apply filters
        status_filter = request.GET.get("status")
        if status_filter:
            promotions = promotions.filter(status=status_filter)

        type_filter = request.GET.get("type")
        if type_filter:
            promotions = promotions.filter(type=type_filter)

        search = request.GET.get("search")
        if search:
            promotions = promotions.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(description__icontains=search)
            )

        promotions = promotions.order_by("-created_at")
        serializer = PromotionSerializer(promotions, many=True)

        return Response(
            {"success": True, "data": serializer.data, "count": promotions.count()}
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_promotion(request):
    """Create a new promotion"""
    try:
        serializer = PromotionSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            promotion = serializer.save(
                company=request.user.company, created_by=request.user
            )

            return Response(
                {
                    "success": True,
                    "data": PromotionSerializer(promotion).data,
                    "message": "Promotion created successfully",
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_promotion(request, promotion_id):
    """Get a specific promotion"""
    try:
        promotion = Promotion.objects.get(id=promotion_id, company=request.user.company)

        serializer = PromotionSerializer(promotion)

        return Response({"success": True, "data": serializer.data})

    except Promotion.DoesNotExist:
        return Response(
            {"success": False, "error": "Promotion not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_promotion(request, promotion_id):
    """Update a promotion"""
    try:
        promotion = Promotion.objects.get(id=promotion_id, company=request.user.company)

        serializer = PromotionSerializer(
            promotion, data=request.data, partial=True, context={"request": request}
        )

        if serializer.is_valid():
            promotion = serializer.save()

            return Response(
                {
                    "success": True,
                    "data": PromotionSerializer(promotion).data,
                    "message": "Promotion updated successfully",
                }
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Promotion.DoesNotExist:
        return Response(
            {"success": False, "error": "Promotion not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_promotion(request, promotion_id):
    """Delete a promotion"""
    try:
        promotion = Promotion.objects.get(id=promotion_id, company=request.user.company)

        # Check if promotion has been used
        if promotion.used_count > 0:
            return Response(
                {
                    "success": False,
                    "error": "Cannot delete a promotion that has been used",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        promotion.delete()

        return Response({"success": True, "message": "Promotion deleted successfully"})

    except Promotion.DoesNotExist:
        return Response(
            {"success": False, "error": "Promotion not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_promotion_status(request, promotion_id):
    """Toggle promotion status between active and inactive"""
    try:
        promotion = Promotion.objects.get(id=promotion_id, company=request.user.company)

        if promotion.status == "active":
            promotion.status = "inactive"
        elif promotion.status == "inactive":
            promotion.status = "active"
        else:
            return Response(
                {
                    "success": False,
                    "error": "Can only toggle between active and inactive status",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        promotion.save()

        return Response(
            {
                "success": True,
                "data": PromotionSerializer(promotion).data,
                "message": f"Promotion status changed to {promotion.status}",
            }
        )

    except Promotion.DoesNotExist:
        return Response(
            {"success": False, "error": "Promotion not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_promotion_code(request):
    """Validate a promotion code and calculate discount"""
    try:
        code = request.data.get("code", "").upper()
        order_value = float(request.data.get("order_value", 0))
        items = request.data.get("items") or []

        if not code:
            return Response(
                {"success": False, "error": "Promotion code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            company = getattr(request.user, "companyId", None) or getattr(
                request.user, "company", None
            )
            promotion = Promotion.objects.get(code=code, company=company)

            if not promotion.can_apply_to_order(order_value):
                return Response(
                    {
                        "success": False,
                        "valid": False,
                        "message": "Promotion cannot be applied to this order",
                        "promotion": PromotionSerializer(promotion).data,
                    }
                )

            discount_amount = promotion.calculate_discount_for_cart(
                order_value, items=items
            )

            return Response(
                {
                    "success": True,
                    "valid": True,
                    "promotion": PromotionSerializer(promotion).data,
                    "discount_amount": float(discount_amount),
                    "final_amount": order_value - float(discount_amount),
                }
            )

        except Promotion.DoesNotExist:
            return Response(
                {"success": False, "valid": False, "message": "Invalid promotion code"}
            )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_promotion_stats(request):
    """Get promotion statistics"""
    try:
        company = getattr(request.user, "companyId", None) or getattr(
            request.user, "company", None
        )
        promotions = Promotion.objects.filter(company=company)
        usage_records = PromotionUsage.objects.filter(promotion__company=company)

        # Calculate statistics
        total_promotions = promotions.count()
        active_promotions = promotions.filter(status="active").count()
        scheduled_promotions = promotions.filter(status="scheduled").count()
        expired_promotions = promotions.filter(status="expired").count()

        total_redemptions = promotions.aggregate(total=Sum("used_count"))["total"] or 0

        total_discount_given = (
            usage_records.aggregate(total=Sum("discount_amount"))["total"] or 0
        )

        # Get top performing promotions
        top_promotions = promotions.order_by("-used_count")[:5]

        # Get expiring promotions (within 7 days)
        expiring_soon = promotions.filter(
            status="active",
            end_date__lte=timezone.now() + timedelta(days=7),
            end_date__gte=timezone.now(),
        )

        stats = {
            "total_promotions": total_promotions,
            "active_promotions": active_promotions,
            "scheduled_promotions": scheduled_promotions,
            "expired_promotions": expired_promotions,
            "total_redemptions": total_redemptions,
            "total_discount_given": float(total_discount_given),
            "average_discount_per_use": float(
                total_discount_given / max(total_redemptions, 1)
            ),
            "top_promotions": PromotionSerializer(top_promotions, many=True).data,
            "expiring_soon": PromotionSerializer(expiring_soon, many=True).data,
            "expiring_count": expiring_soon.count(),
        }

        return Response({"success": True, "data": stats})

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_promotion_usage(request, promotion_id=None):
    """Get promotion usage history"""
    try:
        usage_query = PromotionUsage.objects.filter(
            promotion__company=request.user.company
        )

        if promotion_id:
            usage_query = usage_query.filter(promotion_id=promotion_id)

        # Apply date filters
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if start_date:
            usage_query = usage_query.filter(used_at__gte=start_date)
        if end_date:
            usage_query = usage_query.filter(used_at__lte=end_date)

        usage_query = usage_query.order_by("-used_at")

        # Pagination
        page_size = int(request.GET.get("page_size", 50))
        page = int(request.GET.get("page", 1))
        start = (page - 1) * page_size
        end = start + page_size

        usage_records = usage_query[start:end]
        total_count = usage_query.count()

        serializer = PromotionUsageSerializer(usage_records, many=True)

        return Response(
            {
                "success": True,
                "data": serializer.data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total_count,
                    "pages": (total_count + page_size - 1) // page_size,
                },
            }
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
