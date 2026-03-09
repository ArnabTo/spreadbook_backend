from import_export.admin import ImportExportModelAdmin
from import_export import fields, resources, exceptions
from import_export.widgets import ForeignKeyWidget

from django.contrib import admin
from django.utils.html import format_html

from company.models import Company, Branch
from .models import Category, Product, Unit
from .models import ProductType, GenericName, Brand, ProductBarcode, ProductBatch
from .models.product_model import (
    NewLabel,
    SaleLabel,
    Size,
    Image,
    Tag,
    Color,
    ProductVariant,
)
from .models.rating_model import Rating
from .models.review_model import Review
from .models.inventory_model import (
    InventoryItem,
    InventoryCategory,
    StockMovement,
    ProductStockMovement,
)


class GenericNameByNameOrCreateWidget(ForeignKeyWidget):
    def __init__(self, model, field="pk", *args, **kwargs):
        super().__init__(model, field, *args, **kwargs)
        self.cache = {}

    def clean(self, value, row=None, *args, **kwargs):
        value = str(value).strip() if value is not None else ""
        if not value:
            return None

        if value in self.cache:
            return self.cache[value]

        existing = (
            GenericName.objects.filter(name__iexact=value).order_by("createdAt").first()
        )
        if existing:
            self.cache[value] = existing
            return existing

        new_obj = GenericName.objects.create(name=value)
        self.cache[value] = new_obj
        return new_obj


class CompanyByNameWidget(ForeignKeyWidget):
    """Look up Company by name (case-insensitive)."""

    def __init__(self, *args, **kwargs):
        super().__init__(Company, "name", *args, **kwargs)
        self._cache = {}

    def clean(self, value, row=None, *args, **kwargs):
        value = str(value).strip() if value is not None else ""
        if not value:
            return None
        key = value.lower()
        if key not in self._cache:
            obj = Company.objects.filter(name__iexact=value).first()
            # Fallback: try numeric PK
            if obj is None and value.isdigit():
                obj = Company.objects.filter(pk=int(value)).first()
            self._cache[key] = obj
        return self._cache[key]


class BranchByNameOrCodeWidget(ForeignKeyWidget):
    """Look up Branch by name first, then by code (case-insensitive)."""

    def __init__(self, *args, **kwargs):
        super().__init__(Branch, "name", *args, **kwargs)
        self._cache = {}

    def clean(self, value, row=None, *args, **kwargs):
        value = str(value).strip() if value is not None else ""
        if not value:
            return None
        key = value.lower()
        if key not in self._cache:
            obj = Branch.objects.filter(name__iexact=value).first()
            if obj is None:
                obj = Branch.objects.filter(code__iexact=value).first()
            # Fallback: try numeric PK
            if obj is None and value.isdigit():
                obj = Branch.objects.filter(pk=int(value)).first()
            self._cache[key] = obj
        return self._cache[key]


class ProductImportResource(resources.ModelResource):
    # foreignkey fields handling
    generic_name = fields.Field(
        attribute="generic_name",
        column_name="generic_name",
        widget=GenericNameByNameOrCreateWidget(GenericName, "name"),
    )
    companyId = fields.Field(
        attribute="companyId",
        column_name="companyId",
        widget=CompanyByNameWidget(),
    )
    branch = fields.Field(
        attribute="branch",
        column_name="branch",
        widget=BranchByNameOrCodeWidget(),
    )
    HEADER_ALIASES = {
        "brand name": "brand_name",
        "dosage form": "dosage_form",
        "generic": "generic_name",
        "company": "companyId",
        "company name": "companyId",
        "company id": "companyId",
        "companyid": "companyId",
        "branch": "branch",
        "branch name": "branch",
        "branch code": "branch",
        "branchid": "branch",
        "branch id": "branch",
        "weight": "weight",
        "manufacturer": "manufacturer",
        "unit price": "price",
        "name": "name",
        "code": "code",
        "sku": "sku",
        "category": "category",
        "quantity": "quantity",
        "in stock": "in_stock",
        "supplier price": "supplier_price",
        "regular price": "regular_price",
        "price sale": "priceSale",
        "description": "description",
        "country": "country",
        "gender": "gender",
        "publish": "publish",
        "taxes": "taxes",
        "inventory type": "inventoryType",
        "total ratings": "totalRatings",
        "total sold": "totalSold",
        "total reviews": "totalReviews",
        "available": "available",
        "sub description": "subDescription",
        "size": "size",
        "color": "color",
        "height": "height",
        "shape": "shape",
        "material type": "material_type",
        "technology": "technology",
        "uses for product": "uses_for_product",
        "mfg date": "mfg_date",
        "exp date": "exp_date",
        "prescription required": "prescription_required",
        "controlled substance": "controlled_substance",
        "strength": "strength",
        "mrp": "mrp",
        "status": "status",
        "count sold": "count_sold",
        "recently sold": "recently_sold",
        "recently added": "recently_added",
        "recently viewed": "recently_viewed",
        "recently updated": "recently_updated",
    }

    class Meta:
        model = Product
        fields = (
            "name",
            "code",
            "sku",
            "category",
            "brand_name",
            "manufacturer",
            "description",
            "price",
            "priceSale",
            "regular_price",
            "supplier_price",
            "taxes",
            "in_stock",
            "quantity",
            "available",
            "totalSold",
            "totalRatings",
            "totalReviews",
            "country",
            "gender",
            "publish",
            "inventoryType",
            "subDescription",
            "dosage_form",
            "strength",
            "weight",
            "size",
            "color",
            "height",
            "shape",
            "material_type",
            "technology",
            "uses_for_product",
            "mfg_date",
            "exp_date",
            "prescription_required",
            "controlled_substance",
            "mrp",
            "status",
            "count_sold",
            "recently_sold",
            "recently_added",
            "recently_viewed",
            "recently_updated",
            "generic_name",
            "companyId",
            "branch",
        )
        import_id_fields = []
        use_bulk = True
        batch_size = 2000
        report_skipped = True
        skip_unchanged = False

    @classmethod
    def _normalize_header(cls, header):
        if not isinstance(header, str):
            return ""
        return " ".join(header.replace("_", " ").strip().split()).lower()

    @staticmethod
    def _has_value(value):
        return value is not None and str(value).strip() != ""

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        if not dataset.headers:
            return

        normalized_headers = []
        for header in dataset.headers:
            normalized = self._normalize_header(header)
            mapped_field = self.HEADER_ALIASES.get(
                normalized, normalized.replace(" ", "_")
            )
            normalized_headers.append(mapped_field)
        dataset.headers = normalized_headers

        # Pre-create GenericName objects in bulk for better performance
        generic_index = None
        try:
            generic_index = normalized_headers.index("generic_name")
        except ValueError:
            pass

        if generic_index is not None:
            existing_generics = set(GenericName.objects.values_list("name", flat=True))
            generics_to_create = set()
            for row in dataset:
                value = (row[generic_index] or "").strip()
                if (
                    value
                    and value not in existing_generics
                    and value not in generics_to_create
                ):
                    generics_to_create.add(value)

            if generics_to_create:
                GenericName.objects.bulk_create(
                    [GenericName(name=name) for name in generics_to_create]
                )
                print(f"Pre-created {len(generics_to_create)} GenericName objects")

    def before_import_row(self, row, **kwargs):
        # Clean price fields if they are strings
        price_fields = ["price", "priceSale", "regular_price", "supplier_price", "mrp"]
        for field in price_fields:
            if field in row and isinstance(row[field], str):
                cleaned = (
                    row[field]
                    .replace(",", "")
                    .replace("৳", "")
                    .replace("$", "")
                    .strip()
                )
                if cleaned:
                    try:
                        row[field] = float(cleaned)
                    except ValueError:
                        row[field] = None

        # Skip row if all mapped fields are empty
        if not any(self._has_value(value) for value in row.values()):
            raise exceptions.ImportError("Skipping empty row")

    def import_row(self, row, instance_loader, **kwargs):
        # Only import fields that exist on the model or are declared on this resource
        model_fields = {f.name for f in self._meta.model._meta.get_fields()}
        # Include column_names declared as resource fields (e.g. companyId, branch, generic_name)
        resource_columns = {f.column_name for f in self.fields.values()}
        allowed_keys = model_fields | resource_columns
        cleaned_row = {k: v for k, v in row.items() if k in allowed_keys}
        return super().import_row(cleaned_row, instance_loader, **kwargs)


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
    resource_class = ProductImportResource

    class ProductBarcodeInline(admin.TabularInline):
        model = ProductBarcode
        extra = 1

    class ProductBatchInline(admin.TabularInline):
        model = ProductBatch
        extra = 0
        autocomplete_fields = ("branch", "supplier")

    class ProductVariantInline(admin.TabularInline):
        model = ProductVariant
        extra = 1
        fields = (
            "size",
            "size_name",
            "size_code",
            "size_qty",
            "color",
            "price",
            "image",
        )

    inlines = (ProductBarcodeInline, ProductBatchInline, ProductVariantInline)

    list_display = (
        "name",
        "code",
        "generic_name",
        "priceSale",
        "regular_price",
        "quantity",
        "supplier_price",
        "price",
        "unit",
        "size",
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
    search_fields = ("name", "code", "sku", "category", "unit__name")
    list_per_page = 20
    list_editable = ("quantity", "priceSale")
    filter_horizontal = ("sizes",)
    ordering = ("-createdAt",)

    # Some deployments previously referenced `branchname` in admin fieldsets.
    # Keep this for backward compatibility so the admin change page doesn't crash.
    readonly_fields = ("branchname",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "companyId",
                    "branch",
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
                    "dosage_form",
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
                "fields": (
                    "category",
                    "generic_name",
                ),
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

    def branchname(self, obj):
        branch = getattr(obj, "branch", None)
        return getattr(branch, "name", "") if branch else ""

    branchname.short_description = "Branch"


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


@admin.register(ProductType)
class ProductTypeAdmin(ImportExportModelAdmin):
    list_display = ("name", "slug", "companyId", "is_active", "createdAt")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    list_per_page = 25


@admin.register(GenericName)
class GenericNameAdmin(ImportExportModelAdmin):
    list_display = ("name", "companyId", "is_active", "createdAt")
    list_filter = ("is_active",)
    search_fields = ("name",)
    list_per_page = 25


@admin.register(Brand)
class BrandAdmin(ImportExportModelAdmin):
    list_display = ("name", "companyId", "is_active", "createdAt")
    list_filter = ("is_active",)
    search_fields = ("name",)
    list_per_page = 25


@admin.register(ProductBarcode)
class ProductBarcodeAdmin(admin.ModelAdmin):
    list_display = ("code", "product", "is_primary", "createdAt")
    list_filter = ("is_primary",)
    search_fields = ("code", "product__name", "product__sku", "product__code")
    autocomplete_fields = ("product",)
    list_per_page = 50


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "branch",
        "batch_no",
        "qty_on_hand",
        "exp_date",
        "receivedAt",
    )
    list_filter = ("branch",)
    search_fields = ("batch_no", "product__name", "product__sku", "product__code")
    autocomplete_fields = ("product", "branch", "supplier")
    list_per_page = 50
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
