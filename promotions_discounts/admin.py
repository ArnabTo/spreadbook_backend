from django.contrib import admin
from django.utils.html import format_html
from .models import Promotion, PromotionUsage


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "type",
        "value_display",
        "status_display",
        "usage_display",
        "date_range",
        "company",
        "created_at",
    ]
    list_filter = ["type", "status", "applicable_on", "company", "created_at"]
    search_fields = ["name", "code", "description"]
    readonly_fields = ["id", "created_at", "updated_at", "usage_percentage"]
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "description", "code", "company", "branch")},
        ),
        (
            "Discount Details",
            {"fields": ("type", "value", "applicable_on", "target_items")},
        ),
        (
            "Conditions",
            {
                "fields": (
                    "min_order_value",
                    "max_discount",
                    "usage_limit",
                    "used_count",
                )
            },
        ),
        ("Schedule", {"fields": ("start_date", "end_date", "status")}),
        (
            "Metadata",
            {
                "fields": ("id", "created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    def value_display(self, obj):
        if obj.type == "percentage":
            return f"{obj.value}%"
        elif obj.type == "fixed":
            return f"${obj.value}"
        elif obj.type == "bogo":
            return "Buy 1 Get 1"
        else:
            return "Free Item"

    value_display.short_description = "Value"

    def status_display(self, obj):
        colors = {
            "active": "green",
            "inactive": "red",
            "scheduled": "orange",
            "expired": "gray",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {};">{}</span>', color, obj.get_status_display()
        )

    status_display.short_description = "Status"

    def usage_display(self, obj):
        percentage = obj.usage_percentage
        color = "red" if percentage > 80 else "orange" if percentage > 60 else "green"
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color,
            obj.used_count,
            obj.usage_limit,
            round(percentage, 1),
        )

    usage_display.short_description = "Usage"

    def date_range(self, obj):
        return f"{obj.start_date.strftime('%Y-%m-%d')} to {obj.end_date.strftime('%Y-%m-%d')}"

    date_range.short_description = "Date Range"

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new promotion
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PromotionUsage)
class PromotionUsageAdmin(admin.ModelAdmin):
    list_display = [
        "promotion",
        "customer",
        "order",
        "discount_amount",
        "order_value",
        "used_at",
    ]
    list_filter = ["promotion", "used_at"]
    search_fields = ["promotion__name", "promotion__code", "customer__name"]
    readonly_fields = ["id", "used_at"]
    date_hierarchy = "used_at"
    ordering = ["-used_at"]

    def has_add_permission(self, request):
        # Usually, promotion usage is created automatically, not manually
        return False
