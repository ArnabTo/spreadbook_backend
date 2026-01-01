from rest_framework import routers, urlpatterns
from .api import ChangelogViewSet


router = routers.DefaultRouter()
router.register('api/changelog', ChangelogViewSet, 'changelog')


urlpatterns = router.urls