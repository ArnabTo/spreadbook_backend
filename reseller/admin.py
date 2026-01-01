from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Reseller, ResellerCommission


@admin.register(Reseller)
class ResellerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "companyName",
        "email",
        "phone",
        "city",
        "country",
        "_commission_display",
        "_status_display",
        "totalClients",
        "_revenue_display",
        "_commission_earned_display",
        "joinedDate",
        "_is_active_display",
    )

    list_filter = (
        "status",
        "country",
        "city",
        "joinedDate",
        "created_at",
    )

    search_fields = (
        "name",
        "companyName",
        "email",
        "phone",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "lastActive",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "companyName",
                    "email",
                    "phone",
                )
            },
        ),
        (
            "Address Information",
            {
                "fields": (
                    "address",
                    "city",
                    "country",
                )
            },
        ),
        (
            "Business Information",
            {
                "fields": (
                    "defaultCommission",
                    "status",
                )
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "totalClients",
                    "totalRevenue",
                    "commissionEarned",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "joinedDate",
                    "lastActive",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    ordering = ("-created_at",)

    def _commission_display(self, obj):
        return f"{obj.defaultCommission}%"

    _commission_display.short_description = "Commission Rate"

    def _status_display(self, obj):
        colors = {
            "active": "#28a745",
            "inactive": "#6c757d",
            "suspended": "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    _status_display.short_description = "Status"

    def _revenue_display(self, obj):
        return f"${obj.totalRevenue:,.2f}"

    _revenue_display.short_description = "Total Revenue"

    def _commission_earned_display(self, obj):
        return f"${obj.commissionEarned:,.2f}"

    _commission_earned_display.short_description = "Commission Earned"

    def _is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Active')
        else:
            return format_html('<span style="color: red;">●</span> Inactive')

    _is_active_display.short_description = "Status"


@admin.register(ResellerCommission)
class ResellerCommissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reseller",
        "client_company",
        "_revenue_display",
        "_commission_rate_display",
        "_commission_amount_display",
        "_paid_status_display",
        "created_at",
    )

    list_filter = (
        "is_paid",
        "reseller",
        "commission_rate",
        "created_at",
        "paid_date",
    )

    search_fields = (
        "reseller__name",
        "reseller__companyName",
        "client_company__name",
    )

    readonly_fields = (
        "commission_amount",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Commission Details",
            {
                "fields": (
                    "reseller",
                    "client_company",
                    "revenue_amount",
                    "commission_rate",
                    "commission_amount",
                )
            },
        ),
        (
            "Payment Information",
            {
                "fields": (
                    "is_paid",
                    "paid_date",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    ordering = ("-created_at",)

    def _revenue_display(self, obj):
        return f"${obj.revenue_amount:,.2f}"

    _revenue_display.short_description = "Revenue Amount"

    def _commission_rate_display(self, obj):
        return f"{obj.commission_rate}%"

    _commission_rate_display.short_description = "Commission Rate"

    def _commission_amount_display(self, obj):
        return f"${obj.commission_amount:,.2f}"

    _commission_amount_display.short_description = "Commission Amount"

    def _paid_status_display(self, obj):
        if obj.is_paid:
            return format_html('<span style="color: green;">✓ Paid</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pending</span>')

    _paid_status_display.short_description = "Payment Status"
