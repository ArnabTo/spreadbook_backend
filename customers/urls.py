from rest_framework import routers
from django.urls import path, include
from .api import CustomerViewSet


router = routers.DefaultRouter()
router.register("api/customers", CustomerViewSet, "customers")

urlpatterns = [
    path("", include(router.urls)),
]
