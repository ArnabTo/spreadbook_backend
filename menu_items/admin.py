from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import MenuItem, MenuCategory


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active", "display_order", "item_count")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    list_editable = ("is_active", "display_order")
    ordering = ("display_order", "name")

    def item_count(self, obj):
        """Count of menu items in this category"""
        count = MenuItem.objects.filter(category=obj.name).count()
        if count > 0:
            url = (
                reverse("admin:menu_items_menuitem_changelist")
                + f"?category__exact={obj.name}"
            )
            return format_html('<a href="{}">{} items</a>', url, count)
        return "0 items"

    item_count.short_description = "Items Count"
    item_count.admin_order_field = "name"


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_code",
        "name",
        "category",
        "formatted_price",
        "formatted_cost",
        "profit_display",
        "available",
        "is_featured",
        "display_order",
        "total_sold",
        "created_at",
    )
    list_filter = (
        "available",
        "is_featured",
        "category",
        "is_vegetarian",
        "is_vegan",
        "contains_gluten",
        "created_at",
    )
    search_fields = ("name", "item_code", "description", "ingredients")
    list_editable = ("available", "is_featured", "display_order")
    readonly_fields = (
        "id",
        "item_code",
        "profit_display",
        "profit_margin_display",
        "markup_percentage_display",
        "total_sold",
        "total_revenue",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "id",
                    "item_code",
                    "name",
                    "category",
                    "description",
                    "short_description",
                )
            },
        ),
        (
            "Pricing & Profitability",
            {
                "fields": (
                    ("price", "cost"),
                    (
                        "profit_display",
                        "profit_margin_display",
                        "markup_percentage_display",
                    ),
                    ("total_sold", "total_revenue"),
                )
            },
        ),
        (
            "Availability & Display",
            {"fields": ("available", "is_featured", "display_order")},
        ),
        (
            "Preparation & Nutrition",
            {
                "fields": ("preparation_time", "calories", "ingredients"),
                "classes": ("collapse",),
            },
        ),
        (
            "Dietary Information",
            {
                "fields": ("is_vegetarian", "is_vegan", "contains_gluten"),
                "classes": ("collapse",),
            },
        ),
        ("Media", {"fields": ("image",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    ordering = ("-created_at", "name")
    list_per_page = 25
    date_hierarchy = "created_at"

    def formatted_price(self, obj):
        """Format price with BDT currency"""
        try:
            if obj.price is not None:
                return f"৳{obj.price:,.2f}"
            return "৳0.00"
        except Exception:
            return "৳0.00"

    formatted_price.short_description = "Price"
    formatted_price.admin_order_field = "price"

    def formatted_cost(self, obj):
        """Format cost with BDT currency"""
        try:
            if obj.cost is not None:
                return f"৳{obj.cost:,.2f}"
            return "৳0.00"
        except Exception:
            return "৳0.00"

    formatted_cost.short_description = "Cost"
    formatted_cost.admin_order_field = "cost"

    def profit_display(self, obj):
        """Display profit with color coding"""
        try:
            profit = obj.profit or 0.0
            color = "green" if profit > 0 else "red" if profit < 0 else "orange"
            return format_html(
                '<span style="color: {};">৳{}</span>', color, f"{profit:,.2f}"
            )
        except (TypeError, AttributeError):
            return format_html('<span style="color: orange;">৳0.00</span>')

    profit_display.short_description = "Profit"
    profit_display.admin_order_field = "price"

    def profit_margin_display(self, obj):
        """Display profit margin percentage"""
        try:
            margin = obj.profit_margin or 0.0
            color = "green" if margin > 30 else "orange" if margin > 15 else "red"
            return format_html(
                '<span style="color: {};">{}</span>', color, f"{margin:.1f}%"
            )
        except (TypeError, AttributeError):
            return format_html('<span style="color: red;">0.0%</span>')

    profit_margin_display.short_description = "Profit Margin"

    def markup_percentage_display(self, obj):
        """Display markup percentage"""
        try:
            markup = obj.markup_percentage or 0.0
            return f"{markup:.1f}%"
        except (TypeError, AttributeError):
            return "0.0%"

    markup_percentage_display.short_description = "Markup %"

    def available_status(self, obj):
        """Display availability with color coding"""
        if obj.available:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Available</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Unavailable</span>'
            )

    available_status.short_description = "Status"
    available_status.admin_order_field = "available"

    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related()

    actions = [
        "make_available",
        "make_unavailable",
        "mark_as_featured",
        "unmark_as_featured",
    ]

    def make_available(self, request, queryset):
        """Bulk action to make items available"""
        updated = queryset.update(available=True)
        self.message_user(request, f"{updated} menu items marked as available.")

    make_available.short_description = "Mark selected items as available"

    def make_unavailable(self, request, queryset):
        """Bulk action to make items unavailable"""
        updated = queryset.update(available=False)
        self.message_user(request, f"{updated} menu items marked as unavailable.")

    make_unavailable.short_description = "Mark selected items as unavailable"

    def mark_as_featured(self, request, queryset):
        """Bulk action to mark as featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} menu items marked as featured.")

    mark_as_featured.short_description = "Mark selected items as featured"

    def unmark_as_featured(self, request, queryset):
        """Bulk action to unmark as featured"""
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} menu items unmarked as featured.")

    unmark_as_featured.short_description = "Remove featured status from selected items"
