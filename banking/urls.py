from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api import BankAccountViewSet

router = DefaultRouter()
router.register(r"api/bank-accounts", BankAccountViewSet, basename="bank-account")

urlpatterns = [
    path("", include(router.urls)),
]
