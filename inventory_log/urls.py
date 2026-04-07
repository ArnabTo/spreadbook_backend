from rest_framework.routers import DefaultRouter
from .api import InventoryLogViewSet

router = DefaultRouter()
router.register(r"api/inventory-logs", InventoryLogViewSet, basename="inventory-log")

urlpatterns = router.urls
