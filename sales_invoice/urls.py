from rest_framework.routers import DefaultRouter

from .api import SalesInvoiceViewSet

router = DefaultRouter()
router.register(
    "api/sales-invoices", SalesInvoiceViewSet, "sales-invoices"
)

urlpatterns = router.urls
