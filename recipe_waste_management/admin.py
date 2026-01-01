from django.contrib import admin
from .models import Recipe, RecipeIngredient, WasteRecord


class RecipeIngredientInline(admin.TabularInline):
    """Inline admin for recipe ingredients"""

    model = RecipeIngredient
    extra = 1
    fields = ("name", "quantity", "unit", "cost")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Admin interface for recipes"""

    list_display = (
        "dish_name",
        "category",
        "serving_size",
        "total_cost",
        "selling_price",
        "profit_margin",
        "created_at",
    )
    list_filter = ("category", "company", "branch", "created_at")
    search_fields = ("dish_name", "category", "instructions")
    readonly_fields = ("id", "total_cost", "profit_margin", "created_at", "updated_at")
    inlines = [RecipeIngredientInline]

    fieldsets = (
        ("Basic Information", {"fields": ("dish_name", "category", "serving_size")}),
        ("Timing", {"fields": ("prep_time", "cook_time")}),
        ("Instructions", {"fields": ("instructions",)}),
        ("Pricing", {"fields": ("total_cost", "selling_price", "profit_margin")}),
        ("Business Relations", {"fields": ("company", "branch", "created_by")}),
        (
            "Timestamps",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        """Auto-assign created_by and company if not set"""
        if not obj.pk:  # New object
            if not obj.created_by:
                obj.created_by = request.user
            if not obj.company and hasattr(request.user, "company"):
                obj.company = request.user.company
        super().save_model(request, obj, form, change)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    """Admin interface for recipe ingredients"""

    list_display = ("name", "recipe", "quantity", "unit", "cost")
    list_filter = ("unit", "recipe__category")
    search_fields = ("name", "recipe__dish_name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(WasteRecord)
class WasteRecordAdmin(admin.ModelAdmin):
    """Admin interface for waste records"""

    list_display = (
        "item_name",
        "date",
        "quantity",
        "unit",
        "cost",
        "reason",
        "company",
    )
    list_filter = ("reason", "unit", "date", "company", "branch")
    search_fields = ("item_name", "notes")
    date_hierarchy = "date"
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (
            "Waste Information",
            {"fields": ("date", "item_name", "quantity", "unit", "cost", "reason")},
        ),
        ("Additional Details", {"fields": ("notes",)}),
        ("Business Relations", {"fields": ("company", "branch", "recorded_by")}),
        (
            "Timestamps",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        """Auto-assign recorded_by and company if not set"""
        if not obj.pk:  # New object
            if not obj.recorded_by:
                obj.recorded_by = request.user
            if not obj.company and hasattr(request.user, "company"):
                obj.company = request.user.company
        super().save_model(request, obj, form, change)
