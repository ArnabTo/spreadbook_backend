from django.contrib import admin
from .models import Supplier, SupplierCategory


@admin.register(SupplierCategory)
class SupplierCategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "companyId",
        "is_active",
        "get_supplier_count",
        "created_at",
        "updated_at",
    ]
    list_filter = ["is_active", "companyId", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["companyId", "name"]

    fieldsets = (
        (
            "Category Information",
            {"fields": ("name", "description", "is_active")},
        ),
        ("Company", {"fields": ("companyId",)}),
    )

    readonly_fields = ["created_at", "updated_at"]

    def get_supplier_count(self, obj):
        """Display the number of suppliers in this category"""
        return obj.suppliers.count()

    get_supplier_count.short_description = "Suppliers"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user has a company, filter by it
        if hasattr(request.user, "companyId") and request.user.companyId:
            qs = qs.filter(companyId=request.user.companyId)
        return qs


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        "supplier_code",
        "name",
        "category",
        "contactPerson",
        "email",
        "phone",
        "status",
        "rating",
        "totalSpent",
        "totalPurchases",
        "created_at",
    ]
    list_filter = ["status", "category", "paymentTerms", "country", "created_at"]
    search_fields = ["name", "supplier_code", "email", "phone", "contactPerson"]
    ordering = ["-created_at", "name"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "supplier_code",
                    "email",
                    "phone",
                    "contactPerson",
                    "image",
                )
            },
        ),
        ("Address Information", {"fields": ("address", "zip_code", "country", "fax")}),
        (
            "Business Information",
            {"fields": ("category", "status", "paymentTerms", "rating")},
        ),
        ("Company & Branch", {"fields": ("companyId", "branchId")}),
        (
            "Financial Information",
            {
                "fields": ("previous_balance", "totalSpent", "totalPurchases"),
                "description": "Financial tracking information",
            },
        ),
    )

    readonly_fields = ["totalPurchases", "created_at", "updated_at"]
    filter_horizontal = ["branchId"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user has a company, filter by it
        if hasattr(request.user, "company") and request.user.company:
            qs = qs.filter(companyId=request.user.company)
        return qs
