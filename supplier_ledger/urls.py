from rest_framework.routers import DefaultRouter
from .api import SupplierLedgerViewSet, SupplierPaymentViewSet

router = DefaultRouter()
router.register(
    "api/supplier-ledger/ledgers",
    SupplierLedgerViewSet,
    basename="supplier-ledger",
)
router.register(
    "api/supplier-ledger/payments",
    SupplierPaymentViewSet,
    basename="supplier-payment",
)

urlpatterns = router.urls
