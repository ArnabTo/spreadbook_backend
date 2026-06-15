from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api import ProformaInvoiceViewSet

router = DefaultRouter()
router.register(r"proforma-invoices", ProformaInvoiceViewSet, basename="proforma-invoice")

urlpatterns = [
    path("api/", include(router.urls)),
]
