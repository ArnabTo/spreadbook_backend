from django.db import models
from utils.models.common_fields import Timestamp
from django.utils.timezone import now
from utils import random
import uuid
from decimal import Decimal


class Category(Timestamp):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"


# Enhanced status choices to match frontend
STATUS_CHOICE = (
    ("draft", "Draft"),
    ("paid", "Paid"),
    ("pending", "Pending"),
    ("overdue", "Overdue"),
)

# Enhanced payment choices to match frontend
PAYMENT_CHOICE = (
    ("cash", "Cash"),
    ("credit_card", "Credit Card"),
    ("debit_card", "Debit Card"),
    ("bank_transfer", "Bank Transfer"),
    ("auto_debit", "Auto-debit"),
    ("check", "Check"),
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("upay", "Upay"),
    ("rocket", "Rocket"),
)

# Expense categories matching frontend
CATEGORY_CHOICE = (
    ("rent", "Rent"),
    ("utilities", "Utilities"),
    ("maintenance", "Maintenance"),
    ("marketing", "Marketing"),
    ("supplies", "Supplies"),
    ("licenses", "Licenses & Permits"),
    ("insurance", "Insurance"),
    ("other", "Other"),
)


class Expense(Timestamp):
    """
    Enhanced Expense model for restaurant expense tracking 🛢
    """

    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense_number = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )

    # Expense details matching frontend interface
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICE,
        default="other",
        help_text="Expense category",
    )
    description = models.CharField(max_length=500, help_text="Expense description")
    vendor = models.CharField(max_length=200, help_text="Vendor or supplier name")

    # Financial fields
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Expense amount",
    )

    # Payment information
    payment_method = models.CharField(
        max_length=50, choices=PAYMENT_CHOICE, default="cash"
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICE, default="pending")

    # Additional fields
    recurring = models.BooleanField(
        default=False, help_text="Is this a recurring expense?"
    )
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")

    # Date fields
    expense_date = models.DateField(default=now, help_text="Date of expense")
    due_date = models.DateField(blank=True, null=True, help_text="Due date for payment")

    # Legacy fields for backward compatibility
    name = models.CharField(max_length=100, null=True, blank=True)
    expenseNumber = models.CharField(max_length=100, null=True, blank=True)
    expense_type = models.CharField(max_length=100, null=True, blank=True)
    subTotal = models.FloatField(default=0, blank=True, null=True)
    totalAmount = models.FloatField(default=0, blank=True, null=True)
    content = models.CharField(max_length=500, null=True, blank=True)
    totalQty = models.IntegerField(default=0, blank=True, null=True)
    advance = models.FloatField(default=0, blank=True, null=True)
    due = models.FloatField(default=0, blank=True, null=True)
    cashAmount = models.FloatField(default=0, blank=True, null=True)
    dueDate = models.DateTimeField(default=now, blank=True, null=True)

    # Timestamps
    createdAt = models.DateTimeField(default=now, blank=True, null=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def generate_expense_number(self):
        """Generate unique expense number"""
        if not self.expense_number:
            # Get the last expense number to generate sequential numbers
            last_expense = (
                Expense.objects.filter(expense_number__isnull=False)
                .order_by("-createdAt")
                .first()
            )

            if last_expense and last_expense.expense_number:
                try:
                    # Extract number from EXP-YYYY format
                    last_num = int(last_expense.expense_number.split("-")[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            # Format: EXP-0001, EXP-0002, etc.
            self.expense_number = f"EXP-{new_num:04d}"

    def save(self, *args, **kwargs):
        """Enhanced save method for expense tracking"""
        # Generate expense number if not exists
        if not self.expense_number:
            self.generate_expense_number()

        # Backward compatibility for legacy fields
        if not self.expenseNumber and self.expense_number:
            self.expenseNumber = self.expense_number

        if not self.totalAmount and self.amount:
            self.totalAmount = float(self.amount)

        # Calculate due amount
        if self.totalAmount and self.advance:
            self.due = self.totalAmount - self.advance

        super(Expense, self).save(*args, **kwargs)

    @property
    def formatted_amount(self):
        """Return formatted amount for display in BDT"""
        return f"৳{self.amount:,.2f}" if self.amount else "৳0.00"

    @property
    def is_overdue(self):
        """Check if expense is overdue"""
        if self.due_date and self.status != "paid":
            return self.due_date < now().date()
        return False

    @property
    def category_display(self):
        """Get category display name"""
        return dict(CATEGORY_CHOICE).get(self.category, self.category)

    @property
    def status_display(self):
        """Get status display name"""
        return dict(STATUS_CHOICE).get(self.status, self.status)

    @property
    def payment_method_display(self):
        """Get payment method display name"""
        return dict(PAYMENT_CHOICE).get(self.payment_method, self.payment_method)

    class Meta:
        ordering = ["-createdAt"]
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"

    def __str__(self):
        return f"{self.expense_number or self.expenseNumber} - {self.description} ({self.formatted_amount})"


class ExpenseItem(models.Model):
    expense_invoice = models.ForeignKey(
        Expense, related_name="items", on_delete=models.CASCADE, blank=True, null=True
    )
    # product = models.ForeignKey(Product, related_name='tracks', on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=100, default="", blank=True, null=True)
    description = models.CharField(max_length=500, default="", blank=True, null=True)
    service = models.CharField(max_length=500, default="", blank=True, null=True)
    quantity = models.IntegerField(default=0, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    code = models.IntegerField(default=0, blank=True, null=True)
    duration = models.IntegerField(default=0, blank=True, null=True)

    updateAt = models.DateTimeField(auto_now=True)
    createDate = models.DateTimeField(default=now, blank=True, null=True)

    # class Meta:
    #      unique_together = ['sell_invoice', 'quantity']
    #      ordering = ['quantity']

    # def __str__(self):
    #      return '%d: %s' % (self.quantity, self.title, )
