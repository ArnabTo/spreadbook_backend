from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .inventory_api import (
    InventoryItemViewSet,
    InventoryCategoryViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()
router.register(r"inventory/items", InventoryItemViewSet, basename="inventory-items")
router.register(
    r"inventory/categories", InventoryCategoryViewSet, basename="inventory-categories"
)
router.register(
    r"inventory/movements", StockMovementViewSet, basename="stock-movements"
)

urlpatterns = [
    path("api/", include(router.urls)),
]
