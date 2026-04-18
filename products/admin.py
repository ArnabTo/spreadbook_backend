from import_export.admin import ImportExportModelAdmin
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from django.contrib import admin
from django.utils.html import format_html
from django.db import transaction
from django.db.models import Sum

from company.models import Company, Branch, Warehouse
from .models import Category, Product, Unit
from .models import ProductType, GenericName, Brand, ProductBarcode, ProductBatch
from .models.product_model import (
    NewLabel,
    ProductSerialItem,
    SaleLabel,
    Size,
    Image,
    Tag,
    Color,
    ProductVariant,
    UnitConversionGroup,
    ProductUnit,
)
from .models.rating_model import Rating
from .models.review_model import Review
from .models.inventory_model import (
    InventoryItem,
    InventoryCategory,
    ProductBranchInventory,
    StockMovement,
    ProductStockMovement,
)


def resolve_company_for_import(raw_value):
    """Resolve company by company_code, name, legacy companyId, or PK."""
    if raw_value is None:
        return None

    if isinstance(raw_value, Company):
        return raw_value

    raw_text = str(raw_value).strip()
    if not raw_text:
        return None

    if raw_text.isdigit():
        company = Company.objects.filter(pk=int(raw_text)).first()
        if company is not None:
            return company

    return (
        Company.objects.filter(company_code__iexact=raw_text).first()
        or Company.objects.filter(name__iexact=raw_text).first()
        or Company.objects.filter(companyId__iexact=raw_text).first()
    )


class GenericNameByNameOrCreateWidget(ForeignKeyWidget):
    def __init__(self, model, field="pk", *args, **kwargs):
        super().__init__(model, field, *args, **kwargs)
        self.cache = {}

    def clean(self, value, row=None, *args, **kwargs):
        value = str(value).strip() if value is not None else ""
        if not value:
            return None

        company = resolve_company_for_import((row or {}).get("companyId"))
        cache_key = (getattr(company, "pk", None), value.lower())

        if cache_key in self.cache:
            return self.cache[cache_key]

        existing = (
            GenericName.objects.filter(
                companyId=company,
                name__iexact=value,
            )
            .order_by("createdAt")
            .first()
        )
        if existing:
            self.cache[cache_key] = existing
            return existing

        new_obj = GenericName.objects.create(name=value, companyId=company)
        self.cache[cache_key] = new_obj
        return new_obj


class CompanyByCodeOrNameWidget(ForeignKeyWidget):
    """Look up Company by company_code, name, legacy companyId, or PK."""

    def __init__(self, *args, **kwargs):
        super().__init__(Company, "company_code", *args, **kwargs)
        self._cache = {}

    def clean(self, value, row=None, *args, **kwargs):
        value = str(value).strip() if value is not None else ""
        if not value:
            return None
        key = value.lower()
        if key not in self._cache:
            self._cache[key] = resolve_company_for_import(value)
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
        company_hint = str((row or {}).get("companyId") or "").strip().lower()
        key = (value.lower(), company_hint)
        if key not in self._cache:
            qs = Branch.objects.all()

            if company_hint:
                company = (
                    Company.objects.filter(company_code__iexact=company_hint).first()
                    or Company.objects.filter(name__iexact=company_hint).first()
                    or Company.objects.filter(companyId__iexact=company_hint).first()
                )
                if company is None and company_hint.isdigit():
                    company = Company.objects.filter(pk=int(company_hint)).first()
                if company is not None:
                    qs = qs.filter(company=company)

            obj = qs.filter(code__iexact=value).first()
            if obj is None:
                obj = qs.filter(name__iexact=value).first()
            # Fallback: try numeric PK
            if obj is None and value.isdigit():
                obj = qs.filter(pk=int(value)).first()
            self._cache[key] = obj
        return self._cache[key]


class UnitConversionGroupByNameWidget(ForeignKeyWidget):
    """Look up UnitConversionGroup by name (case-insensitive)."""

    def __init__(self, *args, **kwargs):
        super().__init__(UnitConversionGroup, "name", *args, **kwargs)
        self._cache = {}

    def clean(self, value, row=None, *args, **kwargs):
        value = str(value).strip() if value is not None else ""
        if not value:
            return None
        key = value.lower()
        if key not in self._cache:
            obj = UnitConversionGroup.objects.filter(name__iexact=value).first()
            # Fallback: try numeric PK (ID)
            if obj is None and value.isdigit():
                obj = UnitConversionGroup.objects.filter(pk=int(value)).first()
            self._cache[key] = obj
        return self._cache[key]


class WarehouseByNameOrCodeWidget(ForeignKeyWidget):
    """Look up Warehouse by name first, then by code (case-insensitive)."""

    def __init__(self, *args, **kwargs):
        super().__init__(Warehouse, "name", *args, **kwargs)
        self._cache = {}

    def clean(self, value, row=None, *args, **kwargs):
        value = str(value).strip() if value is not None else ""
        if not value:
            return None
        key = value.lower()
        if key not in self._cache:
            obj = Warehouse.objects.filter(name__iexact=value).first()
            if obj is None:
                obj = Warehouse.objects.filter(code__iexact=value).first()
            # Fallback: try numeric PK
            if obj is None and value.isdigit():
                obj = Warehouse.objects.filter(pk=int(value)).first()
            self._cache[key] = obj
        return self._cache[key]


class UnitByNameOrIdWidget(ForeignKeyWidget):
    """Look up Unit by name or ID (case-insensitive)."""

    def __init__(self, model, field="name", *args, **kwargs):
        super().__init__(model, field, *args, **kwargs)
        self._cache = {}

    def clean(self, value, row=None, *args, **kwargs):
        value = str(value).strip() if value is not None else ""
        if not value:
            return None
        key = value.lower()
        if key not in self._cache:
            # Try by name first (case-insensitive)
            obj = Unit.objects.filter(name__iexact=value).first()
            # Fallback: try numeric PK (ID)
            if obj is None and value.isdigit():
                obj = Unit.objects.filter(pk=int(value)).first()
            self._cache[key] = obj
        return self._cache[key]


class DisplayUnitByNameOrIdWidget(ForeignKeyWidget):
    """Look up Unit by name or ID for display_unit field (case-insensitive)."""

    def __init__(self, model, field="name", *args, **kwargs):
        super().__init__(model, field, *args, **kwargs)
        self._cache = {}

    def clean(self, value, row=None, *args, **kwargs):
        value = str(value).strip() if value is not None else ""
        if not value:
            return None
        key = value.lower()
        if key not in self._cache:
            # Try by name first (case-insensitive)
            obj = Unit.objects.filter(name__iexact=value).first()
            # Fallback: try numeric PK (ID)
            if obj is None and value.isdigit():
                obj = Unit.objects.filter(pk=int(value)).first()
            self._cache[key] = obj
        return self._cache[key]


class ProductImportResource(resources.ModelResource):
    """
    Enhanced resource for importing products with proper field mappings and
    bulk StockSummary creation using atomic transactions.

    Features:
    - Maps stock_quantity → in_stock
    - Proper price field parsing (handles strings with currency symbols)
    - Supports unit and display_unit by name or ID
    - Bulk creates StockSummary records with atomic transactions
    - Recalculates in_stock from StockSummary aggregates
    """

    # Foreign key lookups
    generic_name = fields.Field(
        attribute="generic_name",
        column_name="generic_name",
        widget=GenericNameByNameOrCreateWidget(GenericName, "name"),
    )
    companyId = fields.Field(
        attribute="companyId",
        column_name="companyId",
        widget=CompanyByCodeOrNameWidget(),
    )
    branch = fields.Field(
        attribute="branch",
        column_name="branch",
        widget=BranchByNameOrCodeWidget(),
    )

    # Unit fields
    unit = fields.Field(
        attribute="unit",
        column_name="unit",
        widget=UnitByNameOrIdWidget(Unit, "name"),
    )
    display_unit = fields.Field(
        attribute="display_unit",
        column_name="display_unit",
        widget=UnitByNameOrIdWidget(Unit, "name"),
    )
    unit_conversion_group = fields.Field(
        attribute="unit_conversion_group",
        column_name="unit_conversion_group",
        widget=UnitConversionGroupByNameWidget(),
    )

    # Unit fields
    low_stock_threshold = fields.Field(
        attribute="low_stock_threshold",
        column_name="low_stock_threshold",
    )

    # Stock location data (for StockSummary creation)
    location_type = fields.Field(
        attribute="location_type",
        column_name="location_type",
    )
    location_id = fields.Field(
        attribute="location_id",
        column_name="location_id",
    )
    stock_quantity = fields.Field(
        attribute="stock_quantity",
        column_name="stock_quantity",
    )

    HEADER_ALIASES = {
        # Generic/brand
        "brand name": "brand_name",
        "brand": "brand_name",
        "generic": "generic_name",
        "generic name": "generic_name",
        # Company/branch
        "company": "companyId",
        "company code": "companyId",
        "company name": "companyId",
        "company id": "companyId",
        "companyid": "companyId",
        "branch": "branch",
        "branch name": "branch",
        "branch code": "branch",
        "branchid": "branch",
        "branch id": "branch",
        # Units
        "unit": "unit",
        "primary unit": "unit",
        "unit name": "unit",
        "display unit": "display_unit",
        "disploy unit": "display_unit",
        # Unit conversion
        "unit conversion group": "unit_conversion_group",
        "unit conversion": "unit_conversion_group",
        # Stock & inventory
        "stock": "stock_quantity",
        "stock quanity": "stock_quantity",
        "stock quantity": "stock_quantity",
        "initial stock": "stock_quantity",
        "in stock": "in_stock",
        "in_stock": "in_stock",
        "low stock threshold": "low_stock_threshold",
        "low sotkc threshold": "low_stock_threshold",
        "low stock": "low_stock_threshold",
        "low_stock_threshold": "low_stock_threshold",
        "quantity": "quantity",
        "quanitty": "quantity",
        "max quantity": "quantity",
        "location type": "location_type",
        "location": "location_type",
        "location id": "location_id",
        "location code": "location_id",
        "warehouse code": "location_id",
        "branch location code": "location_id",
        "warehouse id": "location_id",
        "branch id": "location_id",
        # Pricing
        "price": "price",
        "unit price": "price",
        "price sale": "priceSale",
        "sale price": "priceSale",
        "priceSale": "priceSale",
        "regular price": "regular_price",
        "supplier price": "supplier_price",
        "mrp": "mrp",
        # Other
        "manufacturer": "manufacturer",
        "dosage form": "dosage_form",
        "name": "name",
        "code": "code",
        "sku": "sku",
        "category": "category",
        "description": "description",
        "country": "country",
        "gender": "gender",
        "publish": "publish",
        "taxes": "taxes",
        "inventory type": "inventoryType",
        "weight": "weight",
        "size": "size",
        "color": "color",
        "mfg date": "mfg_date",
        "exp date": "exp_date",
        "strength": "strength",
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
            "dosage_form",
            "description",
            "price",
            "priceSale",
            "regular_price",
            "supplier_price",
            "taxes",
            "in_stock",
            "quantity",
            "generic_name",
            "companyId",
            "branch",
            "unit",
            "display_unit",
            "low_stock_threshold",
        )
        import_id_fields = ("companyId", "code")
        use_bulk = True
        batch_size = 2000
        report_skipped = True
        skip_unchanged = False

    def get_bulk_update_fields(self):
        """Restrict bulk update to real Product model fields only."""
        model_fields = {f.name for f in self._meta.model._meta.get_fields()}
        base_fields = super().get_bulk_update_fields()
        return [field_name for field_name in base_fields if field_name in model_fields]

    def _resolve_company(self, raw_value):
        """Resolve company lookup values to a Company instance or None."""
        return resolve_company_for_import(raw_value)

    def get_instance(self, instance_loader, row):
        """Find an existing product by company and code before import."""
        company_value = row.get("companyId")
        code = row.get("code")
        company = self._resolve_company(company_value)

        if company is not None and self._has_value(code):
            code_value = str(code).strip()
            if code_value:
                cache_key = (getattr(company, "pk", company), code_value.lower())
                if not hasattr(self, "_product_instance_cache"):
                    self._product_instance_cache = {}
                if cache_key not in self._product_instance_cache:
                    self._product_instance_cache[cache_key] = Product.objects.filter(
                        companyId=company,
                        code__iexact=code_value,
                    ).first()
                instance = self._product_instance_cache[cache_key]
                if instance is not None:
                    return instance
        return super().get_instance(instance_loader, row)

    @classmethod
    def _normalize_header(cls, header):
        """Normalize header text for comparison."""
        if not isinstance(header, str):
            return ""
        return " ".join(header.replace("_", " ").strip().split()).lower()

    @staticmethod
    def _has_value(value):
        """Check if a value is non-empty."""
        return value is not None and str(value).strip() != ""

    def _row_has_meaningful_data(self, row):
        """Return True when at least one real product input column has a value."""
        meaningful_keys = (
            "name",
            "code",
            "sku",
            "category",
            "generic_name",
            "brand_name",
            "manufacturer",
            "description",
            "dosage_form",
            "strength",
            "price",
            "priceSale",
            "regular_price",
            "supplier_price",
            "mrp",
            "taxes",
            "quantity",
            "in_stock",
            "stock_quantity",
            "companyId",
            "branch",
            "unit",
            "display_unit",
            "unit_conversion_group",
            "location_type",
            "location_id",
            "mfg_date",
            "exp_date",
        )
        return any(self._has_value(row.get(key)) for key in meaningful_keys)

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        """Normalize headers and pre-create shared references."""
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

        # Remove empty worksheet tail rows up front so the preview does not show
        # thousands of skipped rows from Excel's expanded used-range.
        original_rows = list(dataset)
        kept_rows = []
        for raw_row in original_rows:
            row_dict = {
                normalized_headers[idx]: raw_row[idx] if idx < len(raw_row) else None
                for idx in range(len(normalized_headers))
            }
            if self._row_has_meaningful_data(row_dict):
                kept_rows.append(raw_row)

        removed_empty_rows = len(original_rows) - len(kept_rows)
        if removed_empty_rows > 0:
            del dataset[:]
            dataset.extend(kept_rows)
            print(f"✓ Ignored {removed_empty_rows} empty spreadsheet rows")

        # Pre-create GenericName objects in bulk
        generic_index = None
        try:
            generic_index = normalized_headers.index("generic_name")
        except ValueError:
            pass

        if generic_index is not None:
            company_index = None
            try:
                company_index = normalized_headers.index("companyId")
            except ValueError:
                pass

            existing_generics = set(
                GenericName.objects.values_list("companyId_id", "name")
            )
            generics_to_create = set()

            for row in dataset:
                value = (row[generic_index] or "").strip()
                company = None
                if company_index is not None and company_index < len(row):
                    company = resolve_company_for_import(row[company_index])
                key = (getattr(company, "pk", None), value)
                if (
                    value
                    and key not in existing_generics
                    and key not in generics_to_create
                ):
                    generics_to_create.add(key)

            if generics_to_create:
                GenericName.objects.bulk_create(
                    [
                        GenericName(name=name, companyId_id=company_id)
                        for company_id, name in generics_to_create
                    ],
                    ignore_conflicts=True,
                )
                print(f"✓ Pre-created {len(generics_to_create)} GenericName objects")

    def before_import_row(self, row, **kwargs):
        """
        Clean and validate row data before import.
        - Map stock_quantity → in_stock
        - Clean price fields
        - Set low_stock_threshold
        - Validate critical fields
        """

        # Skip blank spreadsheet rows (common with formatted Excel ranges).
        # Without this guard, auto-generated code would convert blank rows into creates.
        if not self._row_has_meaningful_data(row):
            row["_skip_import_row"] = True
            return

        # Stock quantity mapping
        stock_quantity = row.get("stock_quantity")
        if self._has_value(stock_quantity):
            try:
                stock_val = int(str(stock_quantity).strip()) if stock_quantity else 0
                row["in_stock"] = max(0, stock_val)
                row["_import_stock_quantity"] = max(0, stock_val)
            except (ValueError, AttributeError, TypeError):
                row["in_stock"] = 0
                row["_import_stock_quantity"] = 0
        else:
            row.pop("stock_quantity", None)
            row.pop("_import_stock_quantity", None)

        # Quantity (max capacity)
        quantity = row.get("quantity")
        if self._has_value(quantity):
            try:
                row["quantity"] = max(0, int(str(quantity).strip()))
            except (ValueError, AttributeError, TypeError):
                row["quantity"] = row.get("in_stock", 0)
        else:
            row.pop("quantity", None)

        # Price field cleanup
        price_fields = ["price", "priceSale", "regular_price", "supplier_price", "mrp"]
        for field in price_fields:
            if field in row:
                value = row[field]
                if isinstance(value, str):
                    cleaned = (
                        value.replace(",", "")
                        .replace("৳", "")
                        .replace("$", "")
                        .replace("€", "")
                        .strip()
                    )
                    if cleaned:
                        try:
                            row[field] = float(cleaned)
                        except ValueError:
                            row[field] = None
                    else:
                        row[field] = None

        # Low stock threshold
        low_stock = row.get("low_stock_threshold")
        if self._has_value(low_stock):
            try:
                row["low_stock_threshold"] = max(0, int(str(low_stock).strip()))
            except (ValueError, AttributeError, TypeError):
                row["low_stock_threshold"] = 20
        else:
            row.pop("low_stock_threshold", None)

        # Auto-generate code if missing (company + branch prefix + random suffix)
        if not self._has_value(row.get("code")):
            import uuid as _uuid

            company_val = str(row.get("companyId") or "").strip()
            branch_val = str(row.get("branch") or "").strip()
            co_prefix = (
                (company_val[:3] if company_val else "CO").upper().replace(" ", "")
            )
            br_prefix = (
                (branch_val[:3] if branch_val else "BR").upper().replace(" ", "")
            )
            suffix = _uuid.uuid4().hex[:6].upper()
            row["code"] = f"{co_prefix}-{br_prefix}-{suffix}"

        # Store location data for StockSummary creation
        row["_import_location_type"] = row.get("location_type")
        row["_import_location_id"] = row.get("location_id")

    def _resolve_location(self, location_type, location_id, company=None):
        """Resolve location by code first, then by name, then by numeric PK."""
        loc_type = str(location_type or "").strip().lower()
        loc_value = str(location_id or "").strip()
        if not loc_type or not loc_value:
            return None, None

        if loc_type == "warehouse":
            qs = Warehouse.objects.all()
            if company is not None:
                qs = qs.filter(company=company)
            warehouse = qs.filter(code__iexact=loc_value).first()
            if warehouse is None:
                warehouse = qs.filter(name__iexact=loc_value).first()
            if warehouse is None and loc_value.isdigit():
                warehouse = qs.filter(pk=int(loc_value)).first()
            return warehouse, None

        if loc_type == "branch":
            qs = Branch.objects.all()
            if company is not None:
                qs = qs.filter(company=company)
            branch = qs.filter(code__iexact=loc_value).first()
            if branch is None:
                branch = qs.filter(name__iexact=loc_value).first()
            if branch is None and loc_value.isdigit():
                branch = qs.filter(pk=int(loc_value)).first()
            return None, branch

        return None, None

    def skip_row(self, instance, original, row, import_validation_errors=None):
        """Skip rows flagged as empty during preprocessing."""
        if row.get("_skip_import_row"):
            return True
        return super().skip_row(
            instance,
            original,
            row,
            import_validation_errors=import_validation_errors,
        )

    def save_instance(self, instance, is_new, using_transactions, dry_run, **kwargs):
        """Collect instances for bulk StockSummary creation."""
        if not hasattr(self, "_instances_for_stock"):
            self._instances_for_stock = []

        self._instances_for_stock.append(
            {
                "instance": instance,
                "row": kwargs.get("row", {}),
            }
        )

        super().save_instance(instance, is_new, using_transactions, dry_run, **kwargs)

    def after_import(self, dataset, result, using_transactions, dry_run, **kwargs):
        """
        Bulk create StockSummary records after all products are imported.
        Uses atomic transaction for consistency and performance.
        """
        if dry_run or not hasattr(self, "_instances_for_stock"):
            return

        instances_data = getattr(self, "_instances_for_stock", [])
        if not instances_data:
            return

        stock_summaries_to_create = []
        affected_product_ids = set()

        for item in instances_data:
            instance = item["instance"]
            row = item["row"]

            if not instance.companyId:
                print(f"⚠ Skipping StockSummary for product {instance.id}: no company")
                continue

            stock_qty = row.get("_import_stock_quantity") or instance.in_stock
            if stock_qty is None:
                stock_qty = 0

            # Pull pricing from the saved instance (already cleaned by before_import_row)
            price_val = instance.price or 0
            price_sale_val = instance.priceSale or 0
            regular_price_val = instance.regular_price or 0
            low_stock_val = instance.low_stock_threshold or 20

            affected_product_ids.add(instance.id)

            location_type = row.get("_import_location_type")
            location_id = row.get("_import_location_id")

            # Case 1: Specific warehouse/branch provided
            if location_type and location_id:
                warehouse, branch = self._resolve_location(
                    location_type,
                    location_id,
                    company=instance.companyId,
                )

                if warehouse is None and branch is None:
                    print(
                        f"⚠ Location not found for product {instance.id}: {location_type} {location_id}"
                    )
                    continue

                if warehouse or branch:
                    stock_summaries_to_create.append(
                        ProductBranchInventory(
                            product=instance,
                            variant=None,
                            warehouse=warehouse,
                            branch=branch,
                            companyId=instance.companyId,
                            location="in_warehouse" if warehouse else "in_branch",
                            quantity=max(0, int(stock_qty)) if stock_qty else 0,
                            price=price_val,
                            priceSale=price_sale_val,
                            regular_price=regular_price_val,
                            low_stock_threshold=low_stock_val,
                        )
                    )

            # Case 2: Use product's warehouse
            elif instance.warehouse:
                stock_summaries_to_create.append(
                    ProductBranchInventory(
                        product=instance,
                        variant=None,
                        warehouse=instance.warehouse,
                        branch=None,
                        companyId=instance.companyId,
                        location="in_warehouse",
                        quantity=max(0, int(stock_qty)) if stock_qty else 0,
                        price=price_val,
                        priceSale=price_sale_val,
                        regular_price=regular_price_val,
                        low_stock_threshold=low_stock_val,
                    )
                )

            # Case 3: Use product's branch
            elif instance.branch:
                stock_summaries_to_create.append(
                    ProductBranchInventory(
                        product=instance,
                        variant=None,
                        warehouse=None,
                        branch=instance.branch,
                        companyId=instance.companyId,
                        location="in_branch",
                        quantity=max(0, int(stock_qty)) if stock_qty else 0,
                        price=price_val,
                        priceSale=price_sale_val,
                        regular_price=regular_price_val,
                        low_stock_threshold=low_stock_val,
                    )
                )

        if not stock_summaries_to_create:
            return

        # Bulk create with atomic transaction
        try:
            with transaction.atomic():
                print(
                    f"⏳ Creating {len(stock_summaries_to_create)} StockSummary records..."
                )

                created = ProductBranchInventory.objects.bulk_create(
                    stock_summaries_to_create, batch_size=2000, ignore_conflicts=True
                )

                print(f"✓ Created {len(created)} ProductBranchInventory records")

                # Recalculate Product.in_stock
                print(
                    f"⏳ Recalculating in_stock for {len(affected_product_ids)} products..."
                )

                for product_id in affected_product_ids:
                    total = (
                        ProductBranchInventory.objects.filter(
                            product_id=product_id
                        ).aggregate(total=Sum("quantity"))["total"]
                    ) or 0
                    Product.objects.filter(pk=product_id).update(in_stock=total)

                print(
                    f"✓ Recalculated in_stock for {len(affected_product_ids)} products"
                )

        except Exception as e:
            print(f"✗ Error creating ProductBranchInventory records: {str(e)}")
            raise

    def import_row(self, row, instance_loader, **kwargs):
        """Filter row to only include valid model fields."""
        model_fields = {f.name for f in self._meta.model._meta.get_fields()}
        resource_columns = {f.column_name for f in self.fields.values()}
        allowed_keys = model_fields | resource_columns

        # Include internal fields used for StockSummary creation
        allowed_keys |= {
            "_import_stock_quantity",
            "_import_location_type",
            "_import_location_id",
            "_skip_import_row",
        }

        cleaned_row = {k: v for k, v in row.items() if k in allowed_keys}
        return super().import_row(cleaned_row, instance_loader, **kwargs)


@admin.register(ProductBranchInventory)
class ProductBranchInventoryAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "branch",
        "price",
        "priceSale",
        "regular_price",
        "in_stock",
        "available",
    )
    list_filter = ("branch",)
    search_fields = ("product__name", "product__code", "branch__name", "branch__code")
    autocomplete_fields = ("product", "branch")
    list_per_page = 50


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
    list_filter = (
        "status",
        "companyId",
        "branch",
        "category",
        "unit",
        "status",
        "supplier",
    )
    search_fields = ("name", "code", "sku", "category", "unit__name")
    list_per_page = 1000
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
                    "warehouse",
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
                    "refundable",
                    "dosage_form",
                    "buying_unit",
                    "selling_unit",
                    "selling_buying_scale",
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
        (
            "Unit",
            {
                "fields": (
                    "unit",
                    "display_unit",
                )
            },
        ),
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


@admin.register(ProductVariant)
class ProductVariantAdmin(ImportExportModelAdmin):
    list_display = ("product", "size")


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


@admin.register(ProductUnit)
class ProductUnitAdmin(ImportExportModelAdmin):
    list_display = ("product",)
    list_filter = ("product",)
    # search_fields = ("product",)
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


@admin.register(ProductSerialItem)
class ProductSerialItemAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "variant", "serial_code", "status")
    list_filter = ("status",)
    list_per_page = 50


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
