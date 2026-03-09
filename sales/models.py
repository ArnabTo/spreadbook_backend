from decimal import Decimal
import uuid
from datetime import datetime

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.timezone import now
from django.contrib.auth import get_user_model

from customers.models import Customer
from products.models import Product
from utils import random
from utils.models.common_fields import Timestamp

User = get_user_model()

PERCENTAGE_VALIDATOR = [MinValueValidator(0), MaxValueValidator(100)]

# Updated status choices for POS orders
STATUS_CHOICE = (
    ("draft", "Draft"),
    ("pending", "Pending"),
    ("confirmed", "Confirmed"),
    ("preparing", "Preparing"),
    ("ready", "Ready"),
    ("served", "Served"),
    ("paid", "Paid"),
    ("cancelled", "Cancelled"),
    ("overdue", "Overdue"),
)

# Updated payment choices with modern options
PAYMENT_CHOICE = (
    ("cash", "Cash"),
    ("card", "Card Payment"),
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("upay", "Upay"),
    ("rocket", "Rocket"),
    ("bank_transfer", "Bank Transfer"),
    ("digital_wallet", "Digital Wallet"),
    ("cod", "Cash on Delivery"),
)

# Order type choices for POS
ORDER_TYPE_CHOICE = (
    # NOTE: Keep underlying values for backward compatibility with existing DB + frontend.
    ("In-Store", "In-Store"),
    ("Pickup", "Pickup"),
    ("Delivery", "Delivery"),
)


class Sale(Timestamp):
    """Enhanced Sale model for POS system 🛢"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenant scoping
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Order identification
    order_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    invoiceNumber = models.CharField(
        max_length=100, null=True, blank=True
    )  # Keep for backward compatibility

    # Secure shareable link token for customer invoice view
    share_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique token for secure invoice sharing via QR code",
    )

    # Order details
    order_type = models.CharField(
        max_length=20, choices=ORDER_TYPE_CHOICE, default="In-Store"
    )
    table_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Table number for In-Store orders",
    )

    # Customer and staff information
    customer = models.ForeignKey(
        Customer,
        related_name="orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Pharmacy / prescription workflow
    prescription = models.ForeignKey(
        "pharmacy.Prescription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )
    served_by = models.ForeignKey(
        User,
        related_name="served_orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Sales reference: the staff member by whose reference this sale was made
    sales_reference = models.ForeignKey(
        User,
        related_name="reference_sales",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Staff member by whose reference this sale was created",
    )

    # Backward compatibility fields
    invoiceFrom = models.ForeignKey(
        User,
        related_name="invoiceFrom",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    invoiceTo = models.ForeignKey(
        Customer,
        related_name="invoiceTo",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # Order status and payment
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICE, default="pending", db_index=True
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICE, default="cash", blank=True, null=True
    )
    is_paid = models.BooleanField(default=False, verbose_name="Is Paid")
    is_return = models.BooleanField(default=False, verbose_name="Is Returned")
    is_return_adjusted = models.BooleanField(
        default=False, verbose_name="Is Refund Adjusted"
    )
    # Financial fields (using legacy field names to avoid migration conflicts)
    taxes = models.FloatField(default=10.0, help_text="Tax rate percentage")
    taxes_value = models.FloatField(default=0, help_text="Calculated tax amount")
    discount = models.FloatField(default=0, help_text="Discount rate percentage")
    discount_amount = models.FloatField(default=0, help_text="Discount amount")

    # Tips / service charge
    service_charge_rate = models.FloatField(
        default=0,
        validators=PERCENTAGE_VALIDATOR,
        help_text="Service charge rate percentage",
    )
    service_charge_amount = models.FloatField(
        default=0, help_text="Calculated service charge amount"
    )
    tip_amount = models.FloatField(default=0, help_text="Tip amount")

    totalQty = models.IntegerField(default=0, help_text="Total quantity of items")
    subTotal = models.FloatField(
        default=0, help_text="Subtotal before tax and discount"
    )
    totalAmount = models.FloatField(default=0, help_text="Final total amount")
    advance = models.FloatField(default=0, blank=True, null=True)
    due = models.FloatField(default=0, blank=True, null=True)
    cashAmount = models.FloatField(default=0, blank=True, null=True)
    shipping = models.FloatField(default=0, blank=True, null=True)
    total = models.FloatField(default=0, help_text="Legacy total field")

    # Currency and additional fields
    currency = models.CharField(max_length=10, default="BDT", help_text="Currency code")
    notes = models.TextField(
        blank=True, null=True, help_text="Special instructions or notes"
    )

    # Kitchen and timing
    estimated_preparation_time = models.PositiveIntegerField(
        default=0, help_text="Estimated prep time in minutes"
    )
    actual_preparation_time = models.PositiveIntegerField(
        null=True, blank=True, help_text="Actual prep time in minutes"
    )
    order_time = models.DateTimeField(
        auto_now_add=True, help_text="When the order was placed"
    )
    ready_time = models.DateTimeField(
        null=True, blank=True, help_text="When the order was ready"
    )
    served_time = models.DateTimeField(
        null=True, blank=True, help_text="When the order was served"
    )

    # Files and additional data
    pdf_file = models.FileField(upload_to="receipts/", blank=True, null=True)
    kot_printed = models.BooleanField(
        default=False, help_text="Whether KOT has been printed"
    )

    # Timestamps
    dueDate = models.DateTimeField(blank=True, null=True)
    updateAt = models.DateTimeField(auto_now=True)
    createDate = models.DateTimeField(default=now, blank=True, null=True)

    # def get_timestamp(self):
    #      epoch = datetime.utcfromtimestamp(0)
    #      delta = self.createDate - epoch
    #      return int(delta.total_seconds())

    def generate_order_number(self):
        """Generate unique order number with atomic operation"""
        if not self.order_number:
            from django.utils import timezone
            from django.db import transaction
            import uuid

            today = timezone.now().date()
            company_id = getattr(self, "companyId_id", None)
            branch_id = getattr(self, "branch_id", None)
            company_part = str(company_id) if company_id else "0"
            branch_part = str(branch_id) if branch_id else "0"
            # Use a shorter date format to keep invoice/order numbers compact.
            date_part = today.strftime("%y%m%d")

            # Use atomic transaction to ensure uniqueness
            with transaction.atomic():
                # Lock the table to prevent race conditions
                last_order = (
                    Sale.objects.select_for_update()
                    .filter(
                        order_number__isnull=False,
                        createDate__date=today,
                        companyId_id=company_id,
                        branch_id=branch_id,
                    )
                    .order_by("-createDate")
                    .first()
                )

                if last_order and last_order.order_number:
                    try:
                        # Extract number from ORD-YYYY format
                        last_num = int(last_order.order_number.split("-")[-1])
                        new_num = last_num + 1
                    except (ValueError, IndexError):
                        new_num = 1
                else:
                    new_num = 1

                # Format (multi-tenant safe):
                # ORD-{companyId}-{branchId}-{YYMMDD}-{N}
                potential_order_number = (
                    f"ORD-{company_part}-{branch_part}-{date_part}-{new_num}"
                )

                # Double-check uniqueness and add timestamp if needed
                while Sale.objects.filter(order_number=potential_order_number).exists():
                    new_num += 1
                    potential_order_number = (
                        f"ORD-{company_part}-{branch_part}-{date_part}-{new_num}"
                    )

                    # Fallback: add unique suffix if we hit too many collisions
                    if new_num > 9999:
                        timestamp_suffix = str(int(timezone.now().timestamp() * 1000))[
                            -6:
                        ]
                        potential_order_number = f"ORD-{company_part}-{branch_part}-{date_part}-{timestamp_suffix}"
                        break

                self.order_number = potential_order_number

    def generate_share_token(self):
        """Generate a unique secure token for invoice sharing"""
        if not self.share_token:
            import secrets

            # Generate a secure random token
            self.share_token = secrets.token_urlsafe(32)
            # Ensure uniqueness
            while Sale.objects.filter(share_token=self.share_token).exists():
                self.share_token = secrets.token_urlsafe(32)

    def calculate_totals(self):
        """Calculate order totals based on items"""
        # Sum up item totals and convert to float
        subtotal_sum = (
            sum(float(item.total_price) for item in self.items.all())
            if hasattr(self, "items")
            else 0
        )

        discount_amount = float(self.discount_amount or 0)
        base_amount = subtotal_sum - discount_amount
        if base_amount < 0:
            base_amount = 0

        self.subTotal = subtotal_sum
        self.taxes_value = (base_amount * float(self.taxes or 0)) / 100
        self.service_charge_amount = (
            base_amount * float(self.service_charge_rate or 0)
        ) / 100
        self.totalAmount = (
            base_amount
            + float(self.taxes_value or 0)
            + float(self.service_charge_amount or 0)
            + float(self.tip_amount or 0)
        )
        self.total = self.totalAmount
        self.totalQty = (
            sum(item.quantity for item in self.items.all())
            if hasattr(self, "items")
            else 0
        )

    def save(self, *args, **kwargs):
        """Enhanced save method for POS orders"""
        # Keep multi-tenant scoping consistent.
        # If a branch is set but companyId is missing, infer companyId from branch.
        if getattr(self, "branch_id", None) and not getattr(self, "companyId_id", None):
            try:
                self.companyId = getattr(self.branch, "company", None)
            except Exception:
                # If branch isn't loaded for some reason, leave as-is.
                pass

        # If both are set but disagree, normalize companyId to match branch.company.
        # (Safer than raising here; keeps older codepaths from crashing.)
        if getattr(self, "branch_id", None) and getattr(self, "companyId_id", None):
            try:
                branch_company_id = getattr(self.branch, "company_id", None)
                if branch_company_id and str(branch_company_id) != str(
                    self.companyId_id
                ):
                    self.companyId_id = branch_company_id
            except Exception:
                pass

        # Generate order number if not exists
        if not self.order_number:
            self.generate_order_number()

        # Generate share token for secure invoice viewing
        if not self.share_token:
            self.generate_share_token()

        # Auto-set invoice number if not provided
        if not self.invoiceNumber and self.order_number:
            if self.order_number.startswith("ORD-"):
                self.invoiceNumber = "INV-" + self.order_number[len("ORD-") :]
            else:
                # Backward-compatible fallback
                self.invoiceNumber = self.order_number.replace("ORD", "INV")

        # Update payment status based on status
        if self.status == "paid":
            self.is_paid = True

        # Calculate due amount (allow advance=0)
        if self.totalAmount is not None and self.advance is not None:
            try:
                self.due = max(float(self.totalAmount) - float(self.advance), 0.0)
            except Exception:
                # Keep existing due on parse errors
                pass

        # Keep derived amounts consistent.
        if self.subTotal is not None:
            base_amount = float(self.subTotal or 0) - float(self.discount_amount or 0)
            if base_amount < 0:
                base_amount = 0

            self.taxes_value = (base_amount / 100) * float(self.taxes or 0)
            self.service_charge_amount = (base_amount / 100) * float(
                self.service_charge_rate or 0
            )
            self.totalAmount = (
                base_amount
                + float(self.taxes_value or 0)
                + float(self.service_charge_amount or 0)
                + float(self.tip_amount or 0)
            )
            self.total = self.totalAmount

        super(Sale, self).save(*args, **kwargs)

    class Meta:
        ordering = ["-createDate"]

    @property
    def total_items(self):
        """Get total number of items in the order"""
        return self.totalQty or 0

    @property
    def is_in_store(self):
        """Check if this is an In-Store order"""
        return self.order_type == "In-Store"

    # Backward compatibility alias
    @property
    def is_dine_in(self):
        """Alias for is_in_store (backward compatibility)"""
        return self.is_in_store

    @property
    def display_name(self):
        """Display name for the order"""
        if self.order_type == "In-Store" and self.table_number:
            return f"Table {self.table_number}"
        elif self.customer:
            return f"{self.customer.name}"
        else:
            return f"{self.get_order_type_display()}"

    # Properties for backward compatibility with new field names
    @property
    def subtotal(self):
        return self.subTotal

    @property
    def tax_rate(self):
        return self.taxes

    @property
    def tax_amount(self):
        return self.taxes_value

    @property
    def total_amount(self):
        return self.totalAmount

    def __str__(self):
        """String representation of the order"""
        order_id = self.order_number or self.invoiceNumber or f"#{str(self.id)[:8]}"
        return f"{order_id} - {self.display_name} ({self.get_status_display()})"


class InvoiceItem(models.Model):
    """Enhanced InvoiceItem model for POS orders"""

    # Core relationships
    sell_invoice = models.ForeignKey(
        Sale, related_name="items", on_delete=models.CASCADE, null=True, blank=True
    )
    product = models.ForeignKey(
        Product,
        related_name="invoice_items",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # MenuItem integration - add foreign key to MenuItem
    menu_item_id = models.CharField(
        max_length=100, null=True, blank=True, help_text="Menu Item UUID"
    )
    menu_item_code = models.CharField(
        max_length=50, null=True, blank=True, help_text="Menu Item Code"
    )

    # Item details
    title = models.CharField(max_length=200, help_text="Item name")
    description = models.CharField(max_length=500, default="", blank=True, null=True)
    category = models.CharField(
        max_length=100, default="", blank=True, null=True, help_text="Menu category"
    )

    # Pricing and quantity (use legacy field names to avoid migration conflicts)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text="Price per unit"
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total price for this item",
    )
    service = models.CharField(max_length=500, default="", blank=True, null=True)
    code = models.IntegerField(default=0, blank=True, null=True)
    duration = models.IntegerField(default=0, blank=True, null=True)

    # Kitchen details
    preparation_time = models.PositiveIntegerField(
        default=0, help_text="Preparation time in minutes"
    )
    special_instructions = models.TextField(
        blank=True, null=True, help_text="Special cooking instructions"
    )

    # Dual-unit / pharmacy: True when quantity is expressed in secondary (smaller) units.
    sold_in_secondary_unit = models.BooleanField(
        default=False,
        help_text=(
            "True when the sold quantity is in secondary units (e.g. Strips), "
            "False when in primary units (e.g. Box)."
        ),
    )

    # ── Product variant tracking (clothing, multi-size products) ──────────────
    # FK to the specific ProductVariant that was sold (nullable for non-variant items).
    variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items",
        help_text="The specific product variant sold (size/color combination).",
    )
    variant_size = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Variant size code as entered in the catalog (e.g. M, L, 32).",
    )
    variant_size_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Variant size display name (e.g. Medium, Large).",
    )
    variant_color = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Variant color (e.g. Red, Blue, #FF5733).",
    )

    # Order status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ("ordered", "Ordered"),
            ("preparing", "Preparing"),
            ("ready", "Ready"),
            ("served", "Served"),
        ],
        default="ordered",
    )

    # Timestamps
    updateAt = models.DateTimeField(auto_now=True)
    createDate = models.DateTimeField(default=now)
    prepared_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """Calculate totals"""
        # Calculate total price
        if self.price and self.quantity:
            self.total = self.price * self.quantity

        super().save(*args, **kwargs)

    # Properties for new field names (backward compatibility)
    @property
    def unit_price(self):
        return self.price

    @property
    def total_price(self):
        return self.total

    def __str__(self):
        return f"{self.quantity}x {self.title} - {self.total_price}"

    class Meta:
        ordering = ["createDate"]
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"


class Refund(Timestamp):
    """Refund/return record for a POS order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    sale = models.ForeignKey(Sale, related_name="refunds", on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        User,
        related_name="created_refunds",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICE, blank=True, null=True
    )
    reason = models.TextField(blank=True, null=True)
    total_amount = models.FloatField(default=0, help_text="Total refund amount")

    # Inventory integration (MegaShop): when True, refunded quantities were added
    # back to products.Product.in_stock at refund creation time.
    restocked_to_inventory = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {str(self.id)[:8]} for {self.sale_id}"


class RefundItem(models.Model):
    """Line item on a refund."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    refund = models.ForeignKey(Refund, related_name="items", on_delete=models.CASCADE)
    invoice_item = models.ForeignKey(
        InvoiceItem,
        related_name="refund_items",
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if self.unit_price and self.quantity:
            self.total = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"RefundItem {self.quantity}x {self.invoice_item_id}"


# class InvoiceTo (models.Model):
#      primary = models.BooleanField(models.BooleanField( default=False, blank=True, null=True))
