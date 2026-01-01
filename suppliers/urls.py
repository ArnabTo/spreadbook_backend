from rest_framework import routers
from django.urls import path, include
from .api import SupplierViewSet


router = routers.DefaultRouter()
router.register("api/suppliers", SupplierViewSet, "suppliers")

urlpatterns = [
    path("", include(router.urls)),
]
