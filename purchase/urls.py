from rest_framework import routers
from .api import PurchaseOrderViewSet, PurchaseRequisitionViewSet, QuickPurchaseViewSet


router = routers.DefaultRouter()
router.register(
    "api/supplychain/purchase/requisitions",
    PurchaseRequisitionViewSet,
    "purchase-requisitions",
)

router.register(
    "api/supplychain/purchase/orders",
    PurchaseOrderViewSet,
    "purchase-orders",
)

router.register(
    "api/supplychain/purchase/quick-purchases",
    QuickPurchaseViewSet,
    "quick-purchases",
)

urlpatterns = router.urls
