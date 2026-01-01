from rest_framework import routers, urlpatterns
from .api import (
     PerformanceViewSet
)

router = routers.DefaultRouter()
router.register('api/employee/perform', PerformanceViewSet, 'performance-get')

urlpatterns = router.urls