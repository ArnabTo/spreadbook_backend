from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Recipe, RecipeIngredient, WasteRecord
from .serializers import (
    RecipeSerializer,
    RecipeIngredientSerializer,
    WasteRecordSerializer,
    RecipeStatsSerializer,
    WasteStatsSerializer,
)


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing recipes"""

    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category", "serving_size"]
    search_fields = ["dish_name", "category", "instructions"]
    ordering_fields = [
        "dish_name",
        "category",
        "total_cost",
        "selling_price",
        "profit_margin",
        "created_at",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Filter recipes by user's company"""
        user = self.request.user
        queryset = Recipe.objects.all().prefetch_related("ingredients")

        # For now, return all recipes - we can add company filtering later if needed
        # if hasattr(user, "company") and user.company:
        #     queryset = queryset.filter(company=user.company)

        return queryset

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get recipe statistics"""
        queryset = self.get_queryset()

        total_recipes = queryset.count()
        if total_recipes == 0:
            stats_data = {
                "total_recipes": 0,
                "avg_profit_margin": 0,
                "highest_margin_recipe": None,
                "lowest_margin_recipe": None,
                "total_recipe_value": 0,
                "avg_prep_time": 0,
                "avg_cook_time": 0,
            }
        else:
            # Calculate statistics
            avg_data = queryset.aggregate(
                avg_profit_margin=Avg("profit_margin"),
                total_value=Sum("selling_price"),
                avg_prep_time=Avg("prep_time"),
                avg_cook_time=Avg("cook_time"),
            )

            highest_margin = queryset.order_by("-profit_margin").first()
            lowest_margin = queryset.order_by("profit_margin").first()

            stats_data = {
                "total_recipes": total_recipes,
                "avg_profit_margin": float(avg_data["avg_profit_margin"] or 0),
                "highest_margin_recipe": (
                    RecipeSerializer(highest_margin).data if highest_margin else None
                ),
                "lowest_margin_recipe": (
                    RecipeSerializer(lowest_margin).data if lowest_margin else None
                ),
                "total_recipe_value": float(avg_data["total_value"] or 0),
                "avg_prep_time": float(avg_data["avg_prep_time"] or 0),
                "avg_cook_time": float(avg_data["avg_cook_time"] or 0),
            }

        serializer = RecipeStatsSerializer(stats_data)
        return Response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a recipe"""
        try:
            original_recipe = self.get_object()

            # Create new recipe
            new_recipe = Recipe.objects.create(
                dish_name=f"{original_recipe.dish_name} (Copy)",
                category=original_recipe.category,
                serving_size=original_recipe.serving_size,
                prep_time=original_recipe.prep_time,
                cook_time=original_recipe.cook_time,
                instructions=original_recipe.instructions,
                selling_price=original_recipe.selling_price,
                company=original_recipe.company,
                branch=original_recipe.branch,
                created_by=request.user,
            )

            # Copy ingredients
            for ingredient in original_recipe.ingredients.all():
                RecipeIngredient.objects.create(
                    recipe=new_recipe,
                    name=ingredient.name,
                    quantity=ingredient.quantity,
                    unit=ingredient.unit,
                    cost=ingredient.cost,
                )

            # Recalculate costs
            new_recipe.save()

            serializer = self.get_serializer(new_recipe)
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
                    "message": "Recipe duplicated successfully",
                }
            )

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["get"])
    def categories(self, request):
        """Get available recipe categories"""
        categories = Recipe.CATEGORY_CHOICES
        return Response(
            {
                "success": True,
                "data": [{"value": code, "label": label} for code, label in categories],
            }
        )


class WasteRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for managing waste records"""

    serializer_class = WasteRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["reason", "unit", "date"]
    search_fields = ["item_name", "notes"]
    ordering_fields = ["date", "item_name", "quantity", "cost", "created_at"]
    ordering = ["-date", "-created_at"]

    def get_queryset(self):
        """Filter waste records by user's company"""
        user = self.request.user
        queryset = WasteRecord.objects.all()

        # For now, return all waste records - we can add company filtering later if needed
        # if hasattr(user, "company") and user.company:
        #     queryset = queryset.filter(company=user.company)

        # Date range filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get waste statistics"""
        queryset = self.get_queryset()

        # Date calculations
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Calculate statistics
        total_waste_cost = queryset.aggregate(total=Sum("cost"))["total"] or 0
        this_month_waste = (
            queryset.filter(date__gte=month_ago).aggregate(total=Sum("cost"))["total"]
            or 0
        )
        this_week_waste = (
            queryset.filter(date__gte=week_ago).aggregate(total=Sum("cost"))["total"]
            or 0
        )
        today_waste = (
            queryset.filter(date=today).aggregate(total=Sum("cost"))["total"] or 0
        )

        # Waste by reason
        waste_by_reason = {}
        for reason_code, reason_label in WasteRecord.REASON_CHOICES:
            cost = (
                queryset.filter(reason=reason_code).aggregate(total=Sum("cost"))[
                    "total"
                ]
                or 0
            )
            waste_by_reason[reason_code] = float(cost)

        # Waste trend (last 30 days)
        waste_trend = []
        for i in range(30):
            date = today - timedelta(days=i)
            daily_waste = (
                queryset.filter(date=date).aggregate(total=Sum("cost"))["total"] or 0
            )
            waste_trend.append({"date": date.isoformat(), "cost": float(daily_waste)})
        waste_trend.reverse()

        # Average daily waste
        avg_daily_waste = this_month_waste / 30 if this_month_waste > 0 else 0

        stats_data = {
            "total_waste_cost": float(total_waste_cost),
            "this_month_waste": float(this_month_waste),
            "this_week_waste": float(this_week_waste),
            "today_waste": float(today_waste),
            "waste_by_reason": waste_by_reason,
            "waste_trend": waste_trend,
            "avg_daily_waste": float(avg_daily_waste),
        }

        serializer = WasteStatsSerializer(stats_data)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def reasons(self, request):
        """Get available waste reasons"""
        reasons = WasteRecord.REASON_CHOICES
        return Response(
            {
                "success": True,
                "data": [{"value": code, "label": label} for code, label in reasons],
            }
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get waste summary by period"""
        period = request.query_params.get("period", "month")  # day, week, month, year

        today = timezone.now().date()

        if period == "day":
            start_date = today
            queryset = self.get_queryset().filter(date=start_date)
        elif period == "week":
            start_date = today - timedelta(days=7)
            queryset = self.get_queryset().filter(date__gte=start_date)
        elif period == "month":
            start_date = today - timedelta(days=30)
            queryset = self.get_queryset().filter(date__gte=start_date)
        else:  # year
            start_date = today - timedelta(days=365)
            queryset = self.get_queryset().filter(date__gte=start_date)

        total_cost = queryset.aggregate(total=Sum("cost"))["total"] or 0
        total_items = queryset.count()

        # Group by reason
        reason_summary = []
        for reason_code, reason_label in WasteRecord.REASON_CHOICES:
            reason_cost = (
                queryset.filter(reason=reason_code).aggregate(total=Sum("cost"))[
                    "total"
                ]
                or 0
            )
            reason_count = queryset.filter(reason=reason_code).count()

            if reason_cost > 0:
                reason_summary.append(
                    {
                        "reason": reason_code,
                        "reason_label": reason_label,
                        "cost": float(reason_cost),
                        "count": reason_count,
                        "percentage": (
                            (float(reason_cost) / float(total_cost)) * 100
                            if total_cost > 0
                            else 0
                        ),
                    }
                )

        return Response(
            {
                "success": True,
                "data": {
                    "period": period,
                    "start_date": start_date.isoformat(),
                    "end_date": today.isoformat(),
                    "total_cost": float(total_cost),
                    "total_items": total_items,
                    "reason_summary": reason_summary,
                },
            }
        )
