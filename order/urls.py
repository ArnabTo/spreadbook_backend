from rest_framework import routers, urlpatterns
from .api import OrderViewSet


router = routers.DefaultRouter()
router.register('api/product/order/list', OrderViewSet, 'order-get')
# router.register('api/product/sales/post', SalePostSet, 'sale-post')
# router.register('api/product/sales/item', SaleItemSet, 'sale-get')

urlpatterns = router.urls