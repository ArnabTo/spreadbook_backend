from rest_framework import routers, urlpatterns
from .api import (WarrentyProductListViewSet,
               RepairViewSet,
               RepairPostSerializerViewSet,
               EnquiryItemsSerialzerViewSet,
               RepairCashViewSet,
               RepairHistoryHistoryViewSet
               )


router = routers.DefaultRouter()
router.register('api/sale/warrenty/list', WarrentyProductListViewSet, 'warrenty-get')
router.register('api/product/repair/list', RepairViewSet, 'repair-get')
router.register('api/product/repair/post', RepairPostSerializerViewSet, 'repair-post')
router.register('api/product/repair/item', EnquiryItemsSerialzerViewSet, 'repair-get')
router.register('api/product/repair/cash', RepairCashViewSet, 'repair-get')
router.register('api/repair/cash/history', RepairHistoryHistoryViewSet, 'repair-history')

urlpatterns = router.urls