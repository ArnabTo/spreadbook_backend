from rest_framework.routers import DefaultRouter

from .api import BankAccountViewSet, CurrencyViewSet, SalesQuotationViewSet

router = DefaultRouter()
router.register("api/sales-quotations/currencies", CurrencyViewSet, "sales-quotation-currencies")
router.register("api/sales-quotations/bank-accounts", BankAccountViewSet, "sales-quotation-bank-accounts")
router.register(
    "api/sales-quotations", SalesQuotationViewSet, "sales-quotations"
)

urlpatterns = router.urls
