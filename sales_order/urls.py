from rest_framework.routers import DefaultRouter

from .api import SalesOrderViewSet

router = DefaultRouter()
router.register(
    "api/sales-orders", SalesOrderViewSet, "sales-orders"
)

urlpatterns = router.urls
