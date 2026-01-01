from django.urls import include, path
from rest_framework import routers

from .api import NotificationViewSet

router = routers.DefaultRouter()
router.register("api/notifications", NotificationViewSet, "notifications")

urlpatterns = [
    path("", include(router.urls)),
]
