from rest_framework import routers
from .api import SystemSettingsViewSet

router = routers.DefaultRouter()
router.register("api/system-settings",
                SystemSettingsViewSet, "system-settings")

urlpatterns = router.urls
