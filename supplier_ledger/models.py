from django.db import models

"""
Supplier Ledger models.

Design:
  - SupplierLedger: one row per Purchase Order (Debit entry — money owed TO supplier)
    Tracks: total_amount (from PO), total_paid (sum of payments), balance (due)
    Scoped to company + optional branch.

  - SupplierPayment: credit entries — payments the shop owner makes to a supplier
    Many payments can be linked to one SupplierLedger. Each payment reduces the balance.

Scope options: company-wide (branch is null) or branch-specific.
"""

import uuid
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.models.common_fields import Timestamp


class SupplierLedger(Timestamp):
    """One ledger account per supplier per Purchase Order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="supplier_ledgers",
        verbose_name=_("Company"),
    )
    # Optional branch scoping — null means company-wide
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplier_ledgers",
        verbose_name=_("Branch"),
        help_text=_("Null = company-wide ledger"),
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.CASCADE,
        related_name="ledger_entries",
        verbose_name=_("Supplier"),
    )
    purchase_order = models.OneToOneField(
        "purchase.PurchaseOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger",
        verbose_name=_("Purchase Order"),
        help_text=_("The PO this ledger entry originates from"),
    )

    # Debit = total amount of the PO (what we owe to the supplier)
    debit_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Debit Amount"),
        help_text=_("Total amount owed (from PO)"),
    )
    # Credit = sum of payments made; computed from related SupplierPayment records
    credit_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Credit Amount"),
        help_text=_("Total paid so far"),
    )
    # Balance = debit - credit (denormalized for fast queries)
    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Balance"),
        help_text=_("Outstanding balance (debit - credit)"),
    )

    notes = models.TextField(null=True, blank=True, verbose_name=_("Notes"))

    po_number = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("PO Number"),
        help_text=_("Snapshot of PO number for display even if PO is deleted"),
    )
    po_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("PO Date"),
    )

    class Meta:
        verbose_name = _("Supplier Ledger")
        verbose_name_plural = _("Supplier Ledgers")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "supplier"]),
            models.Index(fields=["company", "branch", "supplier"]),
            models.Index(fields=["balance"]),
        ]

    def __str__(self):
        return f"Ledger {self.po_number or self.id} — {self.supplier}"

    def recalc(self):
        """Recompute credit_amount and balance from related payments. Saves."""
        total_paid = (
            self.payments.filter(is_cancelled=False)
            .aggregate(total=models.Sum("amount"))
            .get("total")
            or Decimal("0.00")
        )
        self.credit_amount = total_paid
        self.balance = self.debit_amount - total_paid
        self.save(update_fields=["credit_amount", "balance", "updated_at"])


PAYMENT_METHOD_CHOICES = [
    ("cash", "Cash"),
    ("bank_transfer", "Bank Transfer"),
    ("cheque", "Cheque"),
    ("mobile_banking", "Mobile Banking"),
    ("online", "Online"),
    ("other", "Other"),
]


def _next_payment_no() -> str:
    """Generate sequential payment number like Payment_0001, Payment_0002 …"""
    last = (
        SupplierPayment.objects.filter(payment_no__startswith="Payment_")
        .order_by("-payment_no")
        .values_list("payment_no", flat=True)
        .first()
    )
    if last:
        try:
            seq = int(last.split("_", 1)[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    else:
        seq = 1
    return f"Payment_{seq:04d}"


class SupplierPayment(Timestamp):
    """A single payment credited against a SupplierLedger entry."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payment_no = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name=_("Payment No"),
        help_text=_(
            "Auto-generated sequential payment number, e.g. Payment_0001"),
    )

    ledger = models.ForeignKey(
        SupplierLedger,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("Ledger"),
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name=_("Amount Paid"),
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default="cash",
        verbose_name=_("Payment Method"),
    )
    payment_date = models.DateField(verbose_name=_("Payment Date"))
    reference = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name=_("Reference"),
        help_text=_("Cheque #, transfer reference, etc."),
    )
    notes = models.TextField(null=True, blank=True)
    is_cancelled = models.BooleanField(
        default=False, verbose_name=_("Cancelled"))

    class Meta:
        verbose_name = _("Supplier Payment")
        verbose_name_plural = _("Supplier Payments")
        ordering = ["-payment_date", "-created_at"]
        indexes = [
            models.Index(fields=["ledger", "is_cancelled"]),
        ]

    def __str__(self):
        return (
            f"Payment ৳{self.amount} on {self.payment_date} "
            f"[{self.get_payment_method_display()}]"
        )

    def save(self, *args, **kwargs):
        if not self.payment_no:
            self.payment_no = _next_payment_no()
        super().save(*args, **kwargs)
        # Keep ledger totals fresh after each payment save
        self.ledger.recalc()

    def delete(self, *args, **kwargs):
        ledger = self.ledger
        super().delete(*args, **kwargs)
        ledger.recalc()
