from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import TableViewSet, TableOccupationViewSet, TableReservationViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r"tables", TableViewSet, basename="table")
router.register(r"occupations", TableOccupationViewSet, basename="occupation")
router.register(r"reservations", TableReservationViewSet, basename="reservation")

urlpatterns = [
    path("api/", include(router.urls)),
]
