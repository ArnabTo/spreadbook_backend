from import_export.admin import ImportExportModelAdmin

from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, Unit
from .models.product_model import NewLabel, SaleLabel, Size, Image, Tag, Color
from .models.rating_model import Rating
from .models.review_model import Review
from .models.inventory_model import (
    InventoryItem,
    InventoryCategory,
    StockMovement,
    ProductStockMovement,
)


@admin.register(ProductStockMovement)
class ProductStockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "movement_type",
        "quantity",
        "previous_stock",
        "new_stock",
        "created_at",
        "created_by",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("product__name", "reason", "reference_number")


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    list_display = (
        "name",
        "code",
        "priceSale",
        "regular_price",
        "quantity",
        "supplier_price",
        "price",
        "unit",
        "category",
        "available",
        "in_stock",
        "_status",
        "supplier",
        "is_publish",
        "createdAt",
        "updateAt",
    )
    list_filter = ("status", "category", "unit", "status", "supplier")
    search_fields = ("name", "category__name", "unit__name")
    list_per_page = 20
    list_editable = ("quantity", "priceSale")
    filter_horizontal = ("sizes",)
    ordering = ("-createdAt",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "brand_name",
                    "manufacturer",
                    "description",
                    "image",
                    "in_stock",
                    "country",
                    "gender",
                    "publish",
                    "taxes",
                    "inventoryType",
                    "sku",
                    "price",
                    "coverUrl",
                    "totalRatings",
                    "totalSold",
                    "totalReviews",
                    "available",
                    "subDescription",
                    "newLabel",
                    "saleLabel",
                    "sizes",
                ),
            },
        ),
        ("Price", {"fields": ("priceSale", "regular_price", "supplier_price")}),
        ("Unit", {"fields": ("unit",)}),
        (
            "Category",
            {
                "fields": ("category",),
            },
        ),
        (
            "Mfg. Date",
            {
                "fields": ("mfg_date",),
            },
        ),
        (
            "Exp. Date",
            {
                "fields": ("exp_date",),
            },
        ),
        (
            "Barcode and QR Code",
            {"classes": ("collapse",), "fields": ("barcode", "qrcode")},
        ),
        (
            "Supplier",
            {
                "fields": ("supplier",),
            },
        ),
        (
            "Other Details",
            {
                "classes": ("collapse",),
                "fields": (
                    "size",
                    "color",
                    "weight",
                    "height",
                    "shape",
                    "material_type",
                    "technology",
                    "uses_for_product",
                ),
            },
        ),
    )

    def _status(self, obj):
        """
        This method is used to display the status of the product status in colord text.
        """
        if obj.out_of_stock is False:
            return format_html(
                '<span style="color: #008000; font-weight: bold;">In Stock</span>'
            )
        elif obj.out_of_stock is True:
            return format_html(
                '<span style="color:#DC143C; font-weight: bold;">Out Of Stock</span>'
            )
        else:
            return obj.status


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    list_per_page = 10


@admin.register(Unit)
class UnitAdmin(ImportExportModelAdmin):
    list_display = ("name", "status")
    list_filter = ("status",)
    search_fields = ("name",)
    list_per_page = 10


@admin.register(Review)
class UnitAdmin(ImportExportModelAdmin):
    list_display = ("name",)
    list_filter = ("name",)
    search_fields = ("name",)
    list_per_page = 10


@admin.register(Rating)
class UnitAdmin(ImportExportModelAdmin):
    list_display = ("name",)
    list_filter = ("name",)
    search_fields = ("name",)
    list_per_page = 10


@admin.register(SaleLabel)
class UnitAdmin(ImportExportModelAdmin):
    list_display = ("content",)
    list_filter = ("content",)
    search_fields = ("content",)
    list_per_page = 10


@admin.register(Tag)
class UnitAdmin(ImportExportModelAdmin):
    list_display = ("content",)
    list_filter = ("content",)
    search_fields = ("content",)
    list_per_page = 10


@admin.register(NewLabel)
class UnitAdmin(ImportExportModelAdmin):
    list_display = ("content",)
    list_filter = ("content",)
    search_fields = ("content",)
    list_per_page = 10


@admin.register(Size)
class UnitAdmin(ImportExportModelAdmin):
    list_display = ("value",)
    list_filter = ("value",)
    search_fields = ("value",)
    list_per_page = 10


@admin.register(Image)
class UnitAdmin(ImportExportModelAdmin):
    list_display = ("id",)
    list_filter = ("id",)
    search_fields = ("id",)
    list_per_page = 10


@admin.register(Color)
class UnitAdmin(ImportExportModelAdmin):
    list_display = ("value",)
    list_filter = ("value",)
    search_fields = ("value",)
    list_per_page = 10


# Inventory Management Admin


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(ImportExportModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    list_per_page = 20


@admin.register(InventoryItem)
class InventoryItemAdmin(ImportExportModelAdmin):
    list_display = (
        "name",
        "category",
        "current_stock",
        "unit",
        "status",
        "cost_per_unit",
        "total_value",
        "supplier",
        "last_updated",
    )
    list_filter = ("status", "category", "unit", "supplier")
    search_fields = ("name", "sku", "description")
    list_per_page = 20
    list_editable = ("current_stock", "cost_per_unit")
    ordering = ("-last_updated",)

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "category", "unit", "sku", "description", "location")},
        ),
        (
            "Stock Information",
            {"fields": ("current_stock", "reorder_level", "max_stock", "status")},
        ),
        ("Cost Information", {"fields": ("cost_per_unit", "total_value")}),
        ("Supplier Information", {"fields": ("supplier",)}),
        ("Product Link", {"classes": ("collapse",), "fields": ("product",)}),
    )

    readonly_fields = ("total_value", "status")


@admin.register(StockMovement)
class StockMovementAdmin(ImportExportModelAdmin):
    list_display = (
        "inventory_item",
        "movement_type",
        "quantity",
        "previous_stock",
        "new_stock",
        "reason",
        "created_at",
        "created_by",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("inventory_item__name", "reason", "notes")
    list_per_page = 50
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
