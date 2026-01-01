from django.contrib import admin

from .models import (
    UnitType,
    Unit,
    ResortReservation,
    HousekeepingTask,
    MaintenanceTicket,
    Activity,
    Package,
    Folio,
    FolioLineItem,
)


admin.site.register(UnitType)
admin.site.register(Unit)
admin.site.register(ResortReservation)
admin.site.register(HousekeepingTask)
admin.site.register(MaintenanceTicket)
admin.site.register(Activity)
admin.site.register(Package)
admin.site.register(Folio)
admin.site.register(FolioLineItem)
