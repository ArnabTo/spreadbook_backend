from rest_framework import routers
from django.urls import path, include
from .api import SupplierViewSet, SupplierCategoryViewSet


router = routers.DefaultRouter()
router.register("api/suppliers", SupplierViewSet, "suppliers")
router.register(
    "api/supplier-categories", SupplierCategoryViewSet, "supplier-categories"
)

urlpatterns = [
    path("", include(router.urls)),
]
