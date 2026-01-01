from rest_framework import routers, urlpatterns
from .api import BankAccountViewSet, TransitionViewSet, GetTransitionViewSet


router = routers.DefaultRouter()
router.register('api/user/fringe/list', BankAccountViewSet, 'bank-get')
router.register('api/product/fringe/history', TransitionViewSet, 'history-post')
router.register('api/product/fringe/history/data', GetTransitionViewSet, 'history-get')
# router.register('api/product/sales/item', SaleItemSet, 'sale-get')

urlpatterns = router.urls