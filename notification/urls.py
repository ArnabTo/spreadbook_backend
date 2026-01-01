from rest_framework import routers, urlpatterns
from .api import NotificationViewSet


router = routers.DefaultRouter()
router.register('api/notification/list', NotificationViewSet, 'company-get')


urlpatterns = router.urls