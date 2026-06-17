from rest_framework.routers import DefaultRouter

from .api import SalesOrderViewSet, SalesOrderRegistryViewSet

router = DefaultRouter()
router.register(
    "api/sales-orders", SalesOrderViewSet, "sales-orders"
)
router.register(
    "api/sales-order-registry", SalesOrderRegistryViewSet, "sales-order-registry"
)

urlpatterns = router.urls
