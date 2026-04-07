from django.db import models
from django.utils import timezone
import uuid
from suppliers.models import Supplier
from .product_model import Product, ProductVariant
from .unit_model import Unit
from company.models import Company, Branch
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class ProductBranchInventory(models.Model):
    """Unified per-location inventory + price overrides for a shared Product catalog.

    One row per (product, variant, warehouse, branch) combination.
    Single source of truth for stock quantities across branches and warehouses.

    Pricing fields (price, priceSale, regular_price) are used for branch rows;
    they default to 0 for warehouse rows.

    The post_save/post_delete signals automatically recalculate Product.in_stock
    as the SUM of all quantity rows for that product.
    """

    LOCATION_CHOICES = (
        ("in_warehouse", "In Warehouse"),
        ("in_branch", "In Branch"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="branch_inventory",
        db_index=True,
    )
    companyId = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="product_branch_inventory",
    )

    # ── Where ──────────────────────────────────────────────────────────────
    # Either branch OR warehouse must be set; both may be NULL for legacy rows.
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_branch_inventory",
        db_index=True,
    )
    warehouse = models.ForeignKey(
        "company.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_branch_inventory",
        db_index=True,
    )
    location = models.CharField(
        max_length=20,
        choices=LOCATION_CHOICES,
        default="in_branch",
        db_index=True,
    )

    # ── What (variant support) ──────────────────────────────────────────────
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
        related_name="branch_inventory",
    )

    # ── Pricing (branch-specific; 0 for warehouse rows) ─────────────────────
    price = models.FloatField(default=0, blank=True, null=True)
    priceSale = models.FloatField(default=0, blank=True, null=True)
    regular_price = models.FloatField(default=0, blank=True, null=True)

    # ── Stock quantity (decimal to support fractional / secondary-unit products)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=1,
        default=0,
        help_text="Stock quantity at this location (supports decimals).",
    )

    low_stock_threshold = models.PositiveIntegerField(default=20)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Branch Inventory"
        verbose_name_plural = "Product Branch Inventories"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "variant", "warehouse", "branch"],
                name="uniq_product_branch_inventory",
            )
        ]
        indexes = [
            models.Index(
                fields=["product", "location"], name="idx_pbi_product_location"
            ),
            models.Index(fields=["warehouse", "product"], name="idx_pbi_wh_product"),
            models.Index(fields=["branch", "product"], name="idx_pbi_branch_product"),
            models.Index(
                fields=["companyId", "product"], name="idx_pbi_company_product"
            ),
        ]

    def __str__(self):
        loc = self.warehouse or self.branch or "unknown"
        variant_str = f" / {self.variant}" if self.variant_id else ""
        return f"{self.product_id}{variant_str} @ {loc}: {self.quantity}"

    # ── Backward-compat properties so legacy code reading .in_stock / .available
    # still works without modification in read paths. ─────────────────────────
    @property
    def in_stock(self):
        return int(self.quantity or 0)

    @property
    def available(self):
        return int(self.quantity or 0)


# ── Signal: auto-recalculate Product.in_stock on inventory change ─────────────


def _recalculate_product_in_stock(product_id):
    """Sum all ProductBranchInventory.quantity rows and update Product.in_stock."""
    from django.db.models import Sum as _Sum

    total = (
        ProductBranchInventory.objects.filter(product_id=product_id).aggregate(
            total=_Sum("quantity")
        )["total"]
    ) or 0
    Product.objects.filter(pk=product_id).update(in_stock=total)


@receiver(post_save, sender=ProductBranchInventory)
def pbi_post_save(sender, instance, **kwargs):
    _recalculate_product_in_stock(instance.product_id)


@receiver(post_delete, sender=ProductBranchInventory)
def pbi_post_delete(sender, instance, **kwargs):
    _recalculate_product_in_stock(instance.product_id)


class InventoryCategory(models.Model):
    """Inventory categories for better organization"""

    # Multi-tenant scoping (MegaShop/SaaS)
    companyId = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="inventory_categories",
    )

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inventory Category"
        verbose_name_plural = "Inventory Categories"

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    """Enhanced inventory management model matching frontend structure"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic Information
    name = models.CharField(max_length=200)

    # Multi-tenant scoping (MegaShop/SaaS)
    companyId = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="inventory_items",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="inventory_items",
    )

    # Category can be optional to match the frontend "No Category" selection.
    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)

    # Stock Information
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Cost Information
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Supplier Information
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Status and Tracking
    STATUS_CHOICES = [
        ("good", "Good Stock"),
        ("medium", "Medium Stock"),
        ("low", "Low Stock"),
        ("critical", "Critical Stock"),
        ("out_of_stock", "Out of Stock"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="good")

    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional fields
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(
        max_length=100, blank=True, null=True
    )  # Storage location

    # Additional tracking fields
    expiry_date = models.DateField(null=True, blank=True)
    warranty_expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    average_usage = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )  # Optional usage tracking

    # Related Product (optional link to existing product system)
    product = models.OneToOneField(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_item",
    )

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        """Override save to calculate total value/status and optionally sync linked Product stock."""
        sync_product = kwargs.pop("sync_product", True)

        # Calculate total value
        self.total_value = self.current_stock * self.cost_per_unit

        # Auto-determine status based on stock levels
        if self.current_stock <= 0:
            self.status = "out_of_stock"
        elif self.current_stock <= self.reorder_level:
            self.status = "critical"
        else:
            # Calculate percentage of max stock
            if self.max_stock > 0:
                percentage = (self.current_stock / self.max_stock) * 100
                if percentage < 30:
                    self.status = "low"
                elif percentage < 60:
                    self.status = "medium"
                else:
                    self.status = "good"
            else:
                self.status = "good"

        super().save(*args, **kwargs)

        # Keep Product.in_stock in sync for POS sales stock display
        # IMPORTANT: only sync when the Product is explicitly scoped to this branch.
        # Shared catalog Products (branch=NULL) must NOT have their global `in_stock`
        # overwritten by a single branch's InventoryItem.
        if (
            sync_product
            and self.product_id
            and getattr(self.product, "branch_id", None)
            and str(getattr(self.product, "branch_id", ""))
            == str(getattr(self.branch, "id", ""))
        ):
            desired_stock = int(self.current_stock)
            product = self.product
            update_fields = []
            if product.in_stock != desired_stock:
                product.in_stock = desired_stock
                update_fields.append("in_stock")
            if self.expiry_date and product.exp_date != self.expiry_date:
                product.exp_date = self.expiry_date
                update_fields.append("exp_date")

            if update_fields:
                product.save(update_fields=update_fields)

    @property
    def stock_percentage(self):
        """Calculate stock percentage of max stock"""
        if self.max_stock > 0:
            return (self.current_stock / self.max_stock) * 100
        return 0

    @property
    def is_low_stock(self):
        """Check if item is at or below reorder level"""
        return self.current_stock <= self.reorder_level

    @property
    def formatted_last_updated(self):
        """Return human-readable last updated time"""
        now = timezone.now()
        diff = now - self.last_updated

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"

    def __str__(self):
        return f"{self.name} - {self.current_stock} {self.unit.name}"


class StockMovement(models.Model):
    """Track all stock movements for audit trail"""

    MOVEMENT_TYPES = [
        ("in", "Stock In"),
        ("out", "Stock Out"),
        ("adjustment", "Stock Adjustment"),
        ("transfer", "Stock Transfer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="movements"
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    previous_stock = models.DecimalField(max_digits=10, decimal_places=2)
    new_stock = models.DecimalField(max_digits=10, decimal_places=2)

    # Additional information
    reason = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)

    # Timestamps and user tracking
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(
        max_length=100, default="System"
    )  # Can be linked to User model later

    class Meta:
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.inventory_item.name} - {self.movement_type} - {self.quantity}"


class ProductStockMovement(models.Model):
    """Track stock movements directly on Product (products-as-stock mode)."""

    MOVEMENT_TYPES = [
        ("in", "Stock In"),
        ("out", "Stock Out"),
        ("adjustment", "Stock Adjustment"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_movements"
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    previous_stock = models.DecimalField(max_digits=10, decimal_places=2)
    new_stock = models.DecimalField(max_digits=10, decimal_places=2)

    reason = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, default="System")

    class Meta:
        verbose_name = "Product Stock Movement"
        verbose_name_plural = "Product Stock Movements"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} - {self.movement_type} - {self.quantity}"
