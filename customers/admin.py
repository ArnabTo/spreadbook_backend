import json

from num2words import num2words

from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils.html import format_html

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    date_hierarchy = "created_at"
    list_display = (
        "name",
        "customer_code",
        "phoneNumber",
        "email",
        "category_badge",
        "status_badge",
        "totalOrders",
        "total_spent_display",
        "loyalty_points_display",
        "lastVisit",
    )
    list_filter = (
        "category",
        "status",
        "gender",
        "created_at",
        "updated_at",
        "lastVisit",
    )
    search_fields = ("name", "customer_code", "phoneNumber", "email", "fullAddress")
    readonly_fields = (
        "customer_code",
        "totalOrders",
        "totalSpent",
        "loyaltyPoints",
        "lastVisit",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "customer_code",
                    "name",
                    "phoneNumber",
                    "email",
                    "gender",
                    "avatarUrl",
                )
            },
        ),
        (
            "Customer Classification",
            {
                "fields": (
                    "category",
                    "status",
                    "companyId",
                    "branch",
                )
            },
        ),
        (
            "Address & Contact",
            {
                "fields": (
                    "fullAddress",
                    "addressType",
                    "city",
                    "zip_code",
                    "company",
                )
            },
        ),
        (
            "Customer Statistics",
            {
                "fields": (
                    "totalOrders",
                    "totalSpent",
                    "loyaltyPoints",
                    "lastVisit",
                )
            },
        ),
        (
            "Payment & Balance",
            {"classes": ("collapse",), "fields": ("balance", "previous_balance")},
        ),
        (
            "Notes & Preferences",
            {"classes": ("collapse",), "fields": ("notes",)},
        ),
        (
            "Timestamps",
            {"classes": ("collapse",), "fields": ("created_at", "updated_at")},
        ),
    )

    list_per_page = 20

    @admin.display(description="Category")
    def category_badge(self, obj):
        colors = {
            "regular": "#6B7280",
            "vip": "#F59E0B",
            "corporate": "#3B82F6",
            "consulate": "#8B5CF6",
        }
        color = colors.get(obj.category, "#6B7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_category_display(),
        )

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "Active": "#10B981",
            "Inactive": "#6B7280",
            "Suspended": "#EF4444",
        }
        color = colors.get(obj.status, "#6B7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.status,
        )

    @admin.display(description="Total Spent", ordering="totalSpent")
    def total_spent_display(self, obj):
        return format_html(
            '<strong style="color: #10B981;">৳{}</strong>',
            f"{float(obj.totalSpent):,.2f}",
        )

    @admin.display(description="Loyalty Points", ordering="loyaltyPoints")
    def loyalty_points_display(self, obj):
        if obj.loyaltyPoints > 0:
            return format_html(
                '<span style="background-color: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 3px; font-weight: bold;">🎁 {} pts</span>',
                obj.loyaltyPoints,
            )
        return format_html('<span style="color: #9CA3AF;">0 pts</span>')

    @admin.display(empty_value="Not Available")
    def total(self, obj):
        result = obj.balance + obj.previous_balance
        return format_html("<b>{}</b> <br> {}", result, num2words(result).capitalize())

    def changelist_view(self, request, extra_context=None):
        """Aggregate new customers per day"""
        chart_data = (
            Customer.objects.annotate(date=TruncDay("created_at"))
            .values("date")
            .annotate(y=Count("id"))
            .order_by("-date")
        )
        # Serialize and attach the chart data to the template context
        as_json = json.dumps(list(chart_data), cls=DjangoJSONEncoder)

        extra_context = extra_context or {"chart_data": as_json}

        # Call the superclass changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        """
        Associate model with current user while saving.
        """
        obj.user = request.user
        super().save_model(request, obj, form, change)
