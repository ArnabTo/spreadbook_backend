from rest_framework.routers import DefaultRouter

from .api import SalesInvoiceViewSet, SalesInvoiceRegistryViewSet

router = DefaultRouter()
router.register(
    "api/sales-invoices", SalesInvoiceViewSet, "sales-invoices"
)
router.register(
    "api/sales-invoice-registry", SalesInvoiceRegistryViewSet, "sales-invoice-registry"
)

urlpatterns = router.urls
