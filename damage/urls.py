from rest_framework import routers, urlpatterns
from .api import (
    DamageProductViewSet,
    DamageProductPostViewSet,
    DamageItemViewSet,
    DamageHistoryViewSet
)


router = routers.DefaultRouter()
router.register('api/damage/list', DamageProductViewSet, 'damage-list')
router.register('api/damage/post', DamageProductPostViewSet, 'damage-post')
router.register('api/damage/item', DamageItemViewSet, 'damage-item')
router.register('api/damage/history', DamageHistoryViewSet, 'damage-history')

urlpatterns = router.urls
