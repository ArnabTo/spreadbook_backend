from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "customer_name",
        "phone",
        "email",
        "date",
        "time",
        "guests",
        "table",
        "status",
        "created_at",
    ]
    list_filter = ["status", "date", "guests", "created_at"]
    search_fields = ["customer_name", "phone", "email", "table"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("Customer Information", {"fields": ("customer_name", "phone", "email")}),
        (
            "Booking Details",
            {"fields": ("date", "time", "guests", "table", "status", "notes")},
        ),
        (
            "System Information",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    actions = ["confirm_bookings", "cancel_bookings", "mark_completed"]

    def confirm_bookings(self, request, queryset):
        updated = queryset.update(status="confirmed")
        self.message_user(request, f"{updated} booking(s) were successfully confirmed.")

    confirm_bookings.short_description = "Confirm selected bookings"

    def cancel_bookings(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"{updated} booking(s) were successfully cancelled.")

    cancel_bookings.short_description = "Cancel selected bookings"

    def mark_completed(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"{updated} booking(s) were marked as completed.")

    mark_completed.short_description = "Mark selected bookings as completed"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

    class Media:
        css = {"all": ("admin/css/custom_booking.css",)}
