from rest_framework import routers, urlpatterns
from .api import PortfolioViewSet


router = routers.DefaultRouter()
router.register('api/post/portfolio', PortfolioViewSet, 'post-get')
# router.register('api/post/blog/', PostViewSet, 'slug')


urlpatterns = router.urls