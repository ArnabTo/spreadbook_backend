from rest_framework import routers, urlpatterns
from .api import (
    ReturnViewSet,
    ReturnProductViewSet,
    ReturnProductPostViewSet,
    ReturnProductItemViewSet,
    ReturnProductHistoryViewSet
)

router = routers.DefaultRouter()
router.register('api/products/return', ReturnProductViewSet, 'return-list')
router.register('api/return/post', ReturnProductPostViewSet, 'return-post')
router.register('api/return/item', ReturnProductItemViewSet, 'return-item')
router.register('api/return/history',
                ReturnProductHistoryViewSet, 'return-history')

urlpatterns = router.urls
