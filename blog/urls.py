from rest_framework import routers, urlpatterns
from .api import PostViewSet


router = routers.DefaultRouter()
router.register('api/post/blog', PostViewSet, 'post-get')
# router.register('api/post/blog/', PostViewSet, 'slug')


urlpatterns = router.urls