from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Table, TableOccupation, TableReservation


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = [
        "number",
        "seats",
        "status_display",
        "section",
        "floor",
        "table_type",
        "current_waiter",
        "occupation_duration",
        "is_active",
    ]
    list_filter = ["status", "section", "floor", "table_type", "is_active", "seats"]
    search_fields = ["number", "section", "table_type"]
    ordering = ["number"]

    fieldsets = (
        ("Basic Information", {"fields": ("number", "seats", "status")}),
        ("Location", {"fields": ("section", "floor", "table_type")}),
        ("Settings", {"fields": ("is_active",)}),
    )

    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            "available": "green",
            "occupied": "red",
            "reserved": "orange",
            "maintenance": "gray",
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, "black"),
            obj.get_status_display(),
        )

    status_display.short_description = "Status"

    def current_waiter(self, obj):
        """Show current waiter if table is occupied"""
        occupation = obj.current_occupation
        return occupation.waiter if occupation else "-"

    current_waiter.short_description = "Current Waiter"

    def occupation_duration(self, obj):
        """Show how long table has been occupied"""
        occupation = obj.current_occupation
        return occupation.duration if occupation else "-"

    occupation_duration.short_description = "Duration"

    actions = ["mark_available", "mark_maintenance"]

    def mark_available(self, request, queryset):
        """Mark selected tables as available"""
        count = queryset.update(status="available")
        self.message_user(request, f"{count} tables marked as available.")

    mark_available.short_description = "Mark selected tables as available"

    def mark_maintenance(self, request, queryset):
        """Mark selected tables as under maintenance"""
        count = queryset.update(status="maintenance")
        self.message_user(request, f"{count} tables marked as under maintenance.")

    mark_maintenance.short_description = "Mark selected tables as under maintenance"


@admin.register(TableOccupation)
class TableOccupationAdmin(admin.ModelAdmin):
    list_display = [
        "table_number",
        "customer_name",
        "party_size",
        "waiter",
        "start_time",
        "duration_display",
        "order_amount_display",
        "is_active",
    ]
    list_filter = ["is_active", "start_time", "waiter", "table__section"]
    search_fields = ["customer_name", "customer_phone", "waiter", "table__number"]
    ordering = ["-start_time"]
    date_hierarchy = "start_time"
    readonly_fields = ["start_time"]

    fieldsets = (
        ("Table Information", {"fields": ("table",)}),
        (
            "Customer Information",
            {"fields": ("customer_name", "customer_phone", "party_size")},
        ),
        ("Service Information", {"fields": ("waiter", "order_amount", "notes")}),
        ("Timing", {"fields": ("start_time", "end_time", "is_active")}),
    )

    def table_number(self, obj):
        return f"Table {obj.table.number}"

    table_number.short_description = "Table"
    table_number.admin_order_field = "table__number"

    def duration_display(self, obj):
        """Display occupation duration"""
        return obj.duration

    duration_display.short_description = "Duration"

    def order_amount_display(self, obj):
        """Display order amount with currency"""
        return f"৳{obj.order_amount:,.2f}"

    order_amount_display.short_description = "Order Amount"
    order_amount_display.admin_order_field = "order_amount"

    actions = ["end_occupation"]

    def end_occupation(self, request, queryset):
        """End selected occupations"""
        count = 0
        for occupation in queryset.filter(is_active=True):
            occupation.end_occupation()
            count += 1
        self.message_user(request, f"{count} occupations ended.")

    end_occupation.short_description = "End selected occupations"


@admin.register(TableReservation)
class TableReservationAdmin(admin.ModelAdmin):
    list_display = [
        "table_number",
        "customer_name",
        "reservation_time",
        "party_size",
        "status_display",
        "is_active_display",
    ]
    list_filter = ["status", "reservation_time", "party_size", "table__section"]
    search_fields = [
        "customer_name",
        "customer_phone",
        "customer_email",
        "table__number",
    ]
    ordering = ["reservation_time"]
    date_hierarchy = "reservation_time"

    fieldsets = (
        ("Table Information", {"fields": ("table",)}),
        (
            "Customer Information",
            {
                "fields": (
                    "customer_name",
                    "customer_phone",
                    "customer_email",
                    "party_size",
                )
            },
        ),
        (
            "Reservation Details",
            {"fields": ("reservation_time", "duration_hours", "status")},
        ),
        ("Special Requirements", {"fields": ("special_requests", "notes")}),
    )

    def table_number(self, obj):
        return f"Table {obj.table.number}"

    table_number.short_description = "Table"
    table_number.admin_order_field = "table__number"

    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            "pending": "orange",
            "confirmed": "green",
            "cancelled": "red",
            "completed": "blue",
            "no_show": "gray",
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, "black"),
            obj.get_status_display(),
        )

    status_display.short_description = "Status"

    def is_active_display(self, obj):
        """Show if reservation is currently active"""
        return obj.is_active

    is_active_display.short_description = "Active"
    is_active_display.boolean = True

    actions = ["confirm_reservation", "cancel_reservation", "mark_no_show"]

    def confirm_reservation(self, request, queryset):
        """Confirm selected reservations"""
        count = queryset.filter(status="pending").update(status="confirmed")
        self.message_user(request, f"{count} reservations confirmed.")

    confirm_reservation.short_description = "Confirm selected reservations"

    def cancel_reservation(self, request, queryset):
        """Cancel selected reservations"""
        count = queryset.exclude(status__in=["cancelled", "completed"]).update(
            status="cancelled"
        )
        self.message_user(request, f"{count} reservations cancelled.")

    cancel_reservation.short_description = "Cancel selected reservations"

    def mark_no_show(self, request, queryset):
        """Mark selected reservations as no show"""
        count = queryset.filter(status="confirmed").update(status="no_show")
        self.message_user(request, f"{count} reservations marked as no show.")

    mark_no_show.short_description = "Mark selected reservations as no show"
