from django.contrib import admin
from .models import Company, Branch, CompanyCustomization


class BranchInline(admin.TabularInline):
    """Inline admin for managing branches within company admin"""

    model = Branch
    extra = 0
    fields = ["name", "code", "phoneNumber", "city", "manager", "is_active"]
    readonly_fields = ["code"]


class CompanyCustomizationInline(admin.StackedInline):
    """Inline admin for managing company customization"""

    model = CompanyCustomization
    extra = 0
    fields = ["primaryColor", "currency", "taxRate", "timezone"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Company model"""

    list_display = [ "id", "name", "email", "phoneNumber", "branch_count", "postedAt"]
    list_filter = ["postedAt", "updateAt"]
    search_fields = ["name", "email", "phoneNumber"]
    readonly_fields = ["postedAt", "updateAt", "branch_count"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "email",
                    "phoneNumber",
                    "fullAddress",
                    "subscriptionStatus",
                    "subscriptionPlan",
                )
            },
        ),
        (
            "Additional Details",
            {
                "fields": (
                    "description",
                    "avatarUrl",
                    "logo",
                    "url",
                )
            },
        ),
        ("Statistics", {"fields": ("branch_count",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("postedAt", "updateAt"), "classes": ("collapse",)}),
    )

    inlines = [BranchInline, CompanyCustomizationInline]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Branch model"""

    list_display = [
        "id",
        "name",
        "code",
        "company",
        "city",
        "manager",
        "is_active",
        "get_company_id",
        "postedAt",
    ]
    list_filter = ["is_active", "company", "city", "postedAt"]
    search_fields = ["name", "code", "phoneNumber", "email"]
    readonly_fields = ["code", "postedAt", "updateAt", "user_count", "full_address"]

    fieldsets = (
        ("Basic Information", {"fields": ("company", "name", "code", "manager")}),
        (
            "Contact Information",
            {
                "fields": (
                    "phoneNumber",
                    "email",
                )
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "fullAddress",
                    "city",
                    "state",
                    "country",
                    "postal_code",
                    "full_address",
                )
            },
        ),
        (
            "Restaurant Details",
            {"fields": ("seating_capacity", "delivery_radius", "opening_hours")},
        ),
        ("Status & Statistics", {"fields": ("is_active", "user_count")}),
        ("Timestamps", {"fields": ("postedAt", "updateAt"), "classes": ("collapse",)}),
    )

    def get_company_id(self, obj):
        """Display company ID in admin list"""
        return obj.company.id if obj.company else None

    get_company_id.short_description = "Company ID"


@admin.register(CompanyCustomization)
class CompanyCustomizationAdmin(admin.ModelAdmin):
    """Admin interface for CompanyCustomization model"""

    list_display = [
        "company",
        "primaryColor",
        "currency",
        "taxRate",
        "timezone",
        "created_at",
    ]
    list_filter = ["currency", "timezone", "created_at"]
    search_fields = ["company__name", "primaryColor"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Company", {"fields": ("company",)}),
        ("UI Customization", {"fields": ("primaryColor",)}),
        ("Business Settings", {"fields": ("currency", "taxRate", "timezone")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
