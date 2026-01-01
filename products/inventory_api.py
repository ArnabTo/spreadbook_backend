from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F
from decimal import Decimal

from .models.inventory_model import InventoryItem, InventoryCategory, StockMovement
from .serializers import (
    InventoryItemSerializer,
    InventoryItemCreateUpdateSerializer,
    InventoryCategorySerializer,
    StockMovementSerializer,
    AddStockSerializer,
    InventoryStatsSerializer,
)


class InventoryCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing inventory categories"""

    queryset = InventoryCategory.objects.filter(is_active=True)
    serializer_class = InventoryCategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]


class InventoryItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing inventory items"""

    queryset = InventoryItem.objects.select_related(
        "category", "unit", "supplier"
    ).all()
    serializer_class = InventoryItemSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sku", "description"]
    ordering_fields = ["name", "current_stock", "last_updated", "cost_per_unit"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return InventoryItemCreateUpdateSerializer
        return InventoryItemSerializer

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """Get items with low stock (at or below reorder level)"""
        low_stock_items = self.queryset.filter(current_stock__lte=F("reorder_level"))
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get inventory statistics"""
        total_items = self.queryset.count()
        low_stock_count = self.queryset.filter(
            current_stock__lte=F("reorder_level")
        ).count()
        out_of_stock_count = self.queryset.filter(current_stock__lte=0).count()
        total_value = self.queryset.aggregate(total=Sum("total_value"))[
            "total"
        ] or Decimal("0.00")
        categories_count = InventoryCategory.objects.filter(is_active=True).count()

        stats_data = {
            "total_items": total_items,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "total_value": total_value,
            "categories_count": categories_count,
        }

        serializer = InventoryStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_stock(self, request, pk=None):
        """Add stock to an inventory item"""
        inventory_item = self.get_object()
        serializer = AddStockSerializer(data=request.data)

        if serializer.is_valid():
            quantity = serializer.validated_data["quantity"]
            reason = serializer.validated_data.get("reason", "Stock addition")
            notes = serializer.validated_data.get("notes", "")
            reference_number = serializer.validated_data.get("reference_number", "")
            expiry_date = serializer.validated_data.get("expiry_date")
            warranty_expiry_date = serializer.validated_data.get("warranty_expiry_date")

            # Record previous stock
            previous_stock = inventory_item.current_stock

            # Update stock
            inventory_item.current_stock += quantity

            # Optional metadata updates
            if expiry_date is not None:
                inventory_item.expiry_date = expiry_date
            if warranty_expiry_date is not None:
                inventory_item.warranty_expiry_date = warranty_expiry_date

            inventory_item.save()

            # Create stock movement record
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type="in",
                quantity=quantity,
                previous_stock=previous_stock,
                new_stock=inventory_item.current_stock,
                reason=reason,
                notes=notes,
                reference_number=reference_number,
                created_by=(
                    request.user.username
                    if request.user.is_authenticated
                    else "Anonymous"
                ),
            )

            # Return updated item
            serializer = self.get_serializer(inventory_item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reduce_stock(self, request, pk=None):
        """Reduce stock from an inventory item"""
        inventory_item = self.get_object()
        serializer = AddStockSerializer(data=request.data)

        if serializer.is_valid():
            quantity = serializer.validated_data["quantity"]
            reason = serializer.validated_data.get("reason", "Stock reduction")
            notes = serializer.validated_data.get("notes", "")
            reference_number = serializer.validated_data.get("reference_number", "")
            expiry_date = serializer.validated_data.get("expiry_date")
            warranty_expiry_date = serializer.validated_data.get("warranty_expiry_date")

            # Check if enough stock available
            if inventory_item.current_stock < quantity:
                return Response(
                    {
                        "error": f"Insufficient stock. Available: {inventory_item.current_stock}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Record previous stock
            previous_stock = inventory_item.current_stock

            # Update stock
            inventory_item.current_stock -= quantity

            # Optional metadata updates
            if expiry_date is not None:
                inventory_item.expiry_date = expiry_date
            if warranty_expiry_date is not None:
                inventory_item.warranty_expiry_date = warranty_expiry_date

            inventory_item.save()

            # Create stock movement record
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type="out",
                quantity=quantity,
                previous_stock=previous_stock,
                new_stock=inventory_item.current_stock,
                reason=reason,
                notes=notes,
                reference_number=reference_number,
                created_by=(
                    request.user.username
                    if request.user.is_authenticated
                    else "Anonymous"
                ),
            )

            # Return updated item
            serializer = self.get_serializer(inventory_item)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        """Get stock movements for an inventory item"""
        inventory_item = self.get_object()
        movements = StockMovement.objects.filter(inventory_item=inventory_item)
        serializer = StockMovementSerializer(movements, many=True)
        return Response(serializer.data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing stock movements (read-only)"""

    queryset = StockMovement.objects.select_related("inventory_item").all()
    serializer_class = StockMovementSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
