from rest_framework.decorators import action
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import models
from django.db.models import Q, Avg, Sum, Count
from django.db.models.functions import Coalesce
from rest_framework.exceptions import PermissionDenied
from common.drf_scoping import (
    apply_company_branch_scope,
    get_allowed_branch_ids_for_user,
    get_company_ids_for_user,
    is_unrestricted_user,
)
from .models import MenuItem, MenuCategory
from .serializers import (
    MenuItemSerializer,
    MenuItemListSerializer,
    MenuItemStatsSerializer,
    MenuItemBulkUpdateSerializer,
    MenuCategorySerializer,
)
from .pagination import MenuItemPagination


class MenuItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing menu items with full CRUD operations
    """

    permission_classes = [IsAuthenticated]

    serializer_class = MenuItemSerializer
    pagination_class = MenuItemPagination
    filter_backends = [SearchFilter, OrderingFilter]

    # Search fields for the SearchFilter
    search_fields = [
        "name",
        "item_code",
        "category",
        "description",
        "short_description",
        "ingredients",
    ]

    # Ordering fields
    ordering_fields = [
        "name",
        "category",
        "price",
        "cost",
        "available",
        "is_featured",
        "total_sold",
        "total_revenue",
        "created_at",
        "updated_at",
        "display_order",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Apply query parameter filters"""
        queryset = MenuItem.objects.all()

        # Apply query parameter filters
        category = self.request.query_params.get("category", None)
        available = self.request.query_params.get("available", None)
        is_featured = self.request.query_params.get("is_featured", None)
        min_price = self.request.query_params.get("min_price", None)
        max_price = self.request.query_params.get("max_price", None)
        is_vegetarian = self.request.query_params.get("is_vegetarian", None)

        if category and category != "all":
            queryset = queryset.filter(category__iexact=category)

        if available is not None:
            queryset = queryset.filter(available=available.lower() == "true")

        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured.lower() == "true")

        if min_price:
            try:
                min_price_val = float(min_price)
                queryset = queryset.filter(price__gte=min_price_val)
            except ValueError:
                pass

        if max_price:
            try:
                max_price_val = float(max_price)
                queryset = queryset.filter(price__lte=max_price_val)
            except ValueError:
                pass

        if is_vegetarian is not None:
            queryset = queryset.filter(is_vegetarian=is_vegetarian.lower() == "true")

        queryset = apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

        return queryset

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
            serializer.save()
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
        elif allowed_branch_ids is not None and len(allowed_branch_ids) == 1:
            branch_id = next(iter(allowed_branch_ids))
            branch = user.branchAccess.get(id=branch_id)

        serializer.save(companyId=company, branch=branch)

    def perform_update(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        company_ids = get_company_ids_for_user(user)
        if not company_ids or str(serializer.instance.companyId_id) not in company_ids:
            raise PermissionDenied("You do not have access to this item")

        branch = serializer.validated_data.get("branch", serializer.instance.branch)
        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if (
            branch is not None
            and allowed_branch_ids is not None
            and str(branch.id) not in allowed_branch_ids
        ):
            raise PermissionDenied("You do not have access to this branch")

        serializer.save(companyId=serializer.instance.companyId)

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == "list":
            return MenuItemListSerializer
        elif self.action in ["bulk_update"]:
            return MenuItemBulkUpdateSerializer
        return MenuItemSerializer

    def list(self, request, *args, **kwargs):
        """Override list method to ensure consistent pagination"""
        queryset = self.filter_queryset(self.get_queryset())

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Fallback for non-paginated response
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Custom search endpoint with advanced filtering"""
        queryset = self.get_queryset()

        # Get search parameters
        search_query = request.query_params.get("search", "")
        category = request.query_params.get("category", "")
        available = request.query_params.get("available", "")
        is_featured = request.query_params.get("is_featured", "")

        # Apply search across multiple fields
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(item_code__icontains=search_query)
                | Q(category__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(ingredients__icontains=search_query)
            )

        # Apply filters
        if category and category != "all":
            queryset = queryset.filter(category__iexact=category)

        if available and available != "all":
            queryset = queryset.filter(available=available.lower() == "true")

        if is_featured and is_featured != "all":
            queryset = queryset.filter(is_featured=is_featured.lower() == "true")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MenuItemListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MenuItemListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def toggle_availability(self, request, pk=None):
        """Toggle menu item availability"""
        menu_item = self.get_object()
        menu_item.available = not menu_item.available
        menu_item.save(update_fields=["available", "updated_at"])

        return Response(
            {
                "message": "Menu item availability toggled successfully",
                "id": str(menu_item.id),
                "available": menu_item.available,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def toggle_featured(self, request, pk=None):
        """Toggle menu item featured status"""
        menu_item = self.get_object()
        menu_item.is_featured = not menu_item.is_featured
        menu_item.save(update_fields=["is_featured", "updated_at"])

        return Response(
            {
                "message": "Menu item featured status toggled successfully",
                "id": str(menu_item.id),
                "is_featured": menu_item.is_featured,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Bulk update multiple menu items"""
        serializer = MenuItemBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item_ids = serializer.validated_data["item_ids"]
        update_data = {
            k: v for k, v in serializer.validated_data.items() if k != "item_ids"
        }

        if update_data:
            updated_count = MenuItem.objects.filter(id__in=item_ids).update(
                **update_data
            )

            return Response(
                {
                    "message": f"Successfully updated {updated_count} menu items",
                    "updated_count": updated_count,
                    "updated_fields": list(update_data.keys()),
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"message": "No fields to update provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get comprehensive menu item statistics"""
        queryset = self.get_queryset()

        # Basic counts
        total_items = queryset.count()
        available_items = queryset.filter(available=True).count()
        unavailable_items = total_items - available_items
        featured_items = queryset.filter(is_featured=True).count()

        # Categories
        categories = queryset.values_list("category", flat=True).distinct()
        total_categories = len(categories)

        # Category distribution
        category_distribution = {}
        for category in categories:
            category_distribution[category] = queryset.filter(category=category).count()

        # Financial aggregations with proper output_field specification
        financial_stats = queryset.aggregate(
            total_revenue=Coalesce(
                Sum("total_revenue"), 0.0, output_field=models.FloatField()
            ),
            total_items_sold=Coalesce(
                Sum("total_sold"), 0, output_field=models.IntegerField()
            ),
            average_price=Coalesce(Avg("price"), 0.0, output_field=models.FloatField()),
            average_cost=Coalesce(Avg("cost"), 0.0, output_field=models.FloatField()),
        )

        # Calculate average profit margin properly
        # Use weighted average based on revenue or simple average of all items
        all_items = queryset.filter(price__gt=0)  # Only items with valid prices
        if all_items.exists():
            # Simple average of profit margins across all items
            profit_margins = []
            for item in all_items:
                if item.price and item.cost is not None:
                    margin = item.profit_margin
                    profit_margins.append(margin)

            if profit_margins:
                average_profit_margin = sum(profit_margins) / len(profit_margins)
            else:
                average_profit_margin = 0.0
        else:
            average_profit_margin = 0.0

        # Top performers
        top_selling_items = queryset.order_by("-total_sold")[:5]
        most_profitable_items = queryset.order_by("-total_revenue")[:5]

        stats_data = {
            "total_items": total_items,
            "available_items": available_items,
            "unavailable_items": unavailable_items,
            "featured_items": featured_items,
            "total_categories": total_categories,
            "total_revenue": financial_stats["total_revenue"],
            "total_items_sold": financial_stats["total_items_sold"],
            "average_price": financial_stats["average_price"],
            "average_cost": financial_stats["average_cost"],
            "average_profit_margin": round(average_profit_margin, 2),
            "category_distribution": category_distribution,
            "top_selling_items": MenuItemListSerializer(
                top_selling_items, many=True
            ).data,
            "most_profitable_items": MenuItemListSerializer(
                most_profitable_items, many=True
            ).data,
        }

        return Response(stats_data)

    @action(detail=False, methods=["get"])
    def categories(self, request):
        """Get all available categories"""
        categories = (
            MenuItem.objects.values_list("category", flat=True)
            .distinct()
            .order_by("category")
        )
        return Response({"categories": list(categories), "count": len(categories)})

    def create(self, request, *args, **kwargs):
        """Override create to handle auto-generation of item_code"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class MenuCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing menu categories
    """

    permission_classes = [IsAuthenticated]

    queryset = MenuCategory.objects.all()
    serializer_class = MenuCategorySerializer

    ordering = ["display_order", "name"]

    def get_queryset(self):
        return apply_company_branch_scope(
            request=self.request,
            queryset=MenuCategory.objects.all(),
            company_id_field="companyId_id",
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
            serializer.save()
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
        elif allowed_branch_ids is not None and len(allowed_branch_ids) == 1:
            branch_id = next(iter(allowed_branch_ids))
            branch = user.branchAccess.get(id=branch_id)

        serializer.save(companyId=company, branch=branch)

    def perform_update(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        company_ids = get_company_ids_for_user(user)
        if not company_ids or str(serializer.instance.companyId_id) not in company_ids:
            raise PermissionDenied("You do not have access to this category")

        branch = serializer.validated_data.get("branch", serializer.instance.branch)
        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if (
            branch is not None
            and allowed_branch_ids is not None
            and str(branch.id) not in allowed_branch_ids
        ):
            raise PermissionDenied("You do not have access to this branch")

        serializer.save(companyId=serializer.instance.companyId)
