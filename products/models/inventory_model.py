from django.db import models
from django.utils import timezone
import uuid
from suppliers.models import Supplier
from .product_model import Product
from .unit_model import Unit
from company.models import Company, Branch


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
        if sync_product and self.product_id:
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
