from django.db import models
from django.utils.timezone import now
from products.models.product_model import Product
from products.models.inventory_model import InventoryItem
from suppliers.models import Supplier
from utils import random
from utils.models.common_fields import Timestamp
import uuid
from decimal import Decimal


class Purchase(Timestamp):
    """
    Purchase model for storing purchase data🛢
    """

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_number = models.CharField(max_length=4, unique=True, null=True, blank=True)
    purchase_id = models.CharField(max_length=8, unique=True, null=True, blank=True)
    purchase_date = models.DateField(verbose_name="Purchase Date", default=now)
    payment_options = (
        ("cash payment", "Cash Payment"),
        ("bank payment", "Bank Payment"),
        ("online payment", "Online Payment"),
    )
    payment_method = models.CharField(
        verbose_name="Payment Type",
        max_length=20,
        choices=payment_options,
        default="cash payment",
    )
    details = models.TextField(verbose_name="Details", null=True, blank=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        """override the save method for logical purposes"""
        # Save the purchase invoice_number, purchase_id with a random code.
        self.invoice_number = random.unique_code(4)
        self.purchase_id = random.unique_code(8)
        super(Purchase, self).save(*args, **kwargs)

    def __str__(self):
        """String for representing the Model object."""
        return f"{self.supplier} {self.purchase_date}"


class PurchaseRequisition(Timestamp):
    """
    Purchase Requisition model for requesting items to be purchased
    """

    PURCHASE_TYPE_CHOICES = (
        ("raw_material", "Raw Material"),
        ("direct_inventory", "Direct Inventory"),
        ("asset", "Company Asset"),
    )

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("converted", "Converted to PO"),
    )

    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pr_number = models.CharField(max_length=20, unique=True, editable=False)
    requested_by = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True, default="")
    purchase_type = models.CharField(
        max_length=20, choices=PURCHASE_TYPE_CHOICES, default="direct_inventory"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    request_date = models.DateField(default=now)
    required_date = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    notes = models.TextField(null=True, blank=True)
    approved_by = models.CharField(max_length=255, null=True, blank=True)
    approved_date = models.DateField(null=True, blank=True)

    # Link to user/company (add these if you have auth)
    # company = models.ForeignKey('company.Company', on_delete=models.CASCADE)
    # creator = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.pr_number:
            # Generate PR number: PR-YYYYMMDD-XXXX
            from datetime import datetime

            date_str = datetime.now().strftime("%Y%m%d")
            # Get last PR number for today
            last_pr = (
                PurchaseRequisition.objects.filter(
                    pr_number__startswith=f"PR-{date_str}"
                )
                .order_by("-pr_number")
                .first()
            )

            if last_pr:
                last_num = int(last_pr.pr_number.split("-")[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            self.pr_number = f"PR-{date_str}-{new_num:04d}"

        super(PurchaseRequisition, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.pr_number} - {self.requested_by}"

    class Meta:
        ordering = ["-request_date"]


class PurchaseRequisitionItem(models.Model):
    """
    Items in a purchase requisition
    """

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requisition = models.ForeignKey(
        PurchaseRequisition, on_delete=models.CASCADE, related_name="items"
    )

    # For direct_inventory type: link to Product (POS menu items)
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True
    )

    # For raw_material/asset types: link to InventoryItem
    inventory_item = models.ForeignKey(
        InventoryItem, on_delete=models.SET_NULL, null=True, blank=True
    )

    # For raw_material/asset type or manual entry
    item_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    required_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.item_name} ({self.quantity} {self.unit})"


class PurchaseOrder(Timestamp):
    """Persistent purchase order generated from requisitions or manual PO creation."""

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("waiting_for_receive", "Waiting for Receive"),
        ("received", "Received"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    po_number = models.CharField(max_length=32, unique=True, editable=False)

    requisition = models.ForeignKey(
        PurchaseRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    warehouse = models.ForeignKey(
        "company.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
        help_text="Warehouse this PO is for (warehouse-level purchasing)",
    )
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="purchase_orders",
    )

    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="pending")
    order_date = models.DateField(default=now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("unpaid", "Unpaid"),
            ("partially_paid", "Partially Paid"),
            ("paid", "Paid"),
        ],
        default="unpaid",
    )
    created_by = models.CharField(max_length=150, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.po_number:
            from datetime import datetime

            date_str = datetime.now().strftime("%Y%m%d")
            last_po = (
                PurchaseOrder.objects.filter(po_number__startswith=f"PO-{date_str}")
                .order_by("-po_number")
                .first()
            )
            if last_po:
                last_num = int(last_po.po_number.split("-")[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.po_number = f"PO-{date_str}-{new_num:04d}"

        super().save(*args, **kwargs)

    def recalc_total(self):
        total = Decimal("0")
        for it in self.items.all():
            total += it.total_price or Decimal("0")
        self.total_amount = total
        self.save(update_fields=["total_amount", "updated_at"])

    def __str__(self):
        return self.po_number


class PurchaseOrderItem(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )

    # Link to inventory/product systems
    inventory_item = models.ForeignKey(
        InventoryItem, on_delete=models.SET_NULL, null=True, blank=True
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True
    )
    # Link to a specific product variant (if product has variants)
    variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_order_items",
        help_text="Specific variant of the product, if applicable",
    )

    name = models.CharField(max_length=255)
    # Variant display info (denormalized for easy display)
    variant_size = models.CharField(max_length=100, null=True, blank=True)
    variant_color = models.CharField(max_length=100, null=True, blank=True)
    variant_unique_code = models.CharField(max_length=32, null=True, blank=True)

    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Product selling price at the time of PO creation",
    )
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    item_status = models.CharField(
        max_length=10,
        choices=[("pending", "Pending"), ("received", "Received")],
        default="pending",
    )
    remarks = models.TextField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    warranty_expiry_date = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        try:
            self.total_price = (self.quantity or 0) * (self.unit_price or 0)
        except Exception:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.name}"


class QuickPurchase(Timestamp):
    """Record an immediate purchase made to fulfill a sale.

    Use case: the shop doesn't have the item in catalog/stock, but the customer
    wants it now. Cashier buys it instantly, bills the customer, and any
    remaining qty can later be converted into a proper Product with stock.
    """

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("converted", "Converted"),
        ("cancelled", "Cancelled"),
    )

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenant scoping (optional; may be null for unrestricted users)
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="quick_purchases",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="quick_purchases",
    )

    # Link back to the sale and invoice item (optional)
    sale = models.ForeignKey(
        "sales.Sale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quick_purchases",
    )
    invoice_item = models.ForeignKey(
        "sales.InvoiceItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quick_purchases",
    )

    # When converted, we attach the created Product.
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quick_purchases",
    )

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, default="", blank=True)
    code = models.CharField(max_length=50, null=True, blank=True)
    sku = models.CharField(max_length=100, null=True, blank=True)

    # Prices
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    qty_purchased = models.PositiveIntegerField(default=0)
    qty_sold = models.PositiveIntegerField(default=0)
    remaining_qty = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"QuickPurchase {str(self.uuid)[:8]} - {self.name} ({self.status})"
