from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api import SalesReturnViewSet

router = DefaultRouter()
router.register(r"sales-returns", SalesReturnViewSet, basename="sales-return")

urlpatterns = [
    path("api/", include(router.urls)),
]
