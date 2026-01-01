from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import (
    RoomTypeViewSet,
    RoomViewSet,
    StayReservationViewSet,
    HousekeepingTaskViewSet,
    FolioViewSet,
    FolioLineItemViewSet,
)

router = DefaultRouter()
router.register("api/hotel/room-types", RoomTypeViewSet, basename="hotel-room-types")
router.register("api/hotel/rooms", RoomViewSet, basename="hotel-rooms")
router.register(
    "api/hotel/reservations", StayReservationViewSet, basename="hotel-reservations"
)
router.register(
    "api/hotel/housekeeping", HousekeepingTaskViewSet, basename="hotel-housekeeping"
)
router.register("api/hotel/folios", FolioViewSet, basename="hotel-folios")
router.register(
    "api/hotel/folio-items", FolioLineItemViewSet, basename="hotel-folio-items"
)

urlpatterns = [
    path("", include(router.urls)),
]
