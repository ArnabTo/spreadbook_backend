from rest_framework import routers, urlpatterns
from .api import (
     DamageProductViewSet,
     DamageProductPostViewSet,
     DamageItemViewSet,
     DamageHistoryViewSet
)


router = routers.DefaultRouter()
router.register('api/damage/list', DamageProductViewSet, 'damage-get')
router.register('api/damage/post', DamageProductPostViewSet, 'damage-post')
router.register('api/damage/item', DamageItemViewSet, 'damage-get')
router.register('api/damage/history', DamageHistoryViewSet, 'damage-get')

urlpatterns = router.urls