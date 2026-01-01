from rest_framework import routers, urlpatterns
from .api import ProjectViewSet



router = routers.DefaultRouter()
router.register('api/project', ProjectViewSet, 'project-get')


urlpatterns = router.urls