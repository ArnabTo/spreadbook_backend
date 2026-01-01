from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import (
    UnitTypeViewSet,
    UnitViewSet,
    ResortReservationViewSet,
    HousekeepingTaskViewSet,
    MaintenanceTicketViewSet,
    ActivityViewSet,
    PackageViewSet,
    FolioViewSet,
    FolioLineItemViewSet,
)

router = DefaultRouter()
router.register("api/resort/unit-types", UnitTypeViewSet, basename="resort-unit-types")
router.register("api/resort/units", UnitViewSet, basename="resort-units")
router.register(
    "api/resort/reservations", ResortReservationViewSet, basename="resort-reservations"
)
router.register(
    "api/resort/housekeeping", HousekeepingTaskViewSet, basename="resort-housekeeping"
)
router.register(
    "api/resort/maintenance", MaintenanceTicketViewSet, basename="resort-maintenance"
)
router.register("api/resort/activities", ActivityViewSet, basename="resort-activities")
router.register("api/resort/packages", PackageViewSet, basename="resort-packages")
router.register("api/resort/folios", FolioViewSet, basename="resort-folios")
router.register(
    "api/resort/folio-items", FolioLineItemViewSet, basename="resort-folio-items"
)

urlpatterns = [
    path("", include(router.urls)),
]
