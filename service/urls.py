from rest_framework import routers, urlpatterns
from .api import ServiceItemViewSet


router = routers.DefaultRouter()
router.register('api/post/service', ServiceItemViewSet, 'post-get')
# router.register('api/post/blog/', PostViewSet, 'slug')


urlpatterns = router.urls