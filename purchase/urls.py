from rest_framework import routers
from .api import PurchaseOrderViewSet, PurchaseRequisitionViewSet


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

urlpatterns = router.urls
