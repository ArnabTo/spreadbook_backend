from django.contrib import admin

from .models import (
    RoomType,
    Room,
    StayReservation,
    HousekeepingTask,
    Folio,
    FolioLineItem,
)


admin.site.register(RoomType)
admin.site.register(Room)
admin.site.register(StayReservation)
admin.site.register(HousekeepingTask)
admin.site.register(Folio)
admin.site.register(FolioLineItem)
