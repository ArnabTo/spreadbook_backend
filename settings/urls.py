from django.urls import path
from rest_framework import routers
from .api import SystemSettingsViewSet, branding_detail

router = routers.DefaultRouter()
router.register("api/system-settings",
                SystemSettingsViewSet, "system-settings")

urlpatterns = router.urls + [
    path("api/branding/", branding_detail, name="branding-detail"),
]
