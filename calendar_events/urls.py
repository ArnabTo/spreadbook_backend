from rest_framework import routers, urlpatterns
from .api import CalendarViewSet


router = routers.DefaultRouter()
router.register('api/calendar', CalendarViewSet, 'post-get')
# router.register('api/post/blog/', PostViewSet, 'slug')


urlpatterns = router.urls