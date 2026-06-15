from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.models.common_fields import Timestamp


class SalesInvoice(Timestamp):
    """Sales Invoice header (company-scoped)."""

    TAX_MODE_CHOICES = (
        ("TAX_INCLUDED", _("Tax Included")),
        ("TAX_EXCLUDED", _("Tax Excluded")),
    )

    BILL_STATUS_CHOICES = (
        ("Draft", _("Draft")),
        ("Pending", _("Pending")),
        ("Approved", _("Approved")),
        ("Rejected", _("Rejected")),
    )

    E_INVOICE_STATUS_CHOICES = (
        ("Draft", _("Draft")),
        ("Sent", _("Sent")),
        ("Generated", _("Generated")),
    )

    INVOICE_TYPE_CHOICES = (
        ("Credit", _("Credit")),
        ("Cash", _("Cash")),
    )

    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_invoices",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_invoices",
    )

    bill_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_invoices",
    )
    currency = models.ForeignKey(
        "sales_quotation.Currency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_invoices",
    )
    currency_rate = models.DecimalField(
        max_digits=18, decimal_places=6, default=Decimal("1")
    )
    financial_year = models.ForeignKey(
        "financial_years.FinancialYear",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_invoices",
    )

    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    delivered_on = models.DateField(null=True, blank=True)
    sales_person = models.ForeignKey(
        "authenticator.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_invoices_as_salesperson",
    )
    po_ref = models.CharField(max_length=100, blank=True, default="")
    so_ref = models.CharField(max_length=100, blank=True, default="")
    dn_ref_no = models.CharField(max_length=100, blank=True, default="")
    project_ref_no = models.CharField(max_length=100, blank=True, default="")
    inv_type = models.CharField(
        max_length=20, choices=INVOICE_TYPE_CHOICES, default="Credit"
    )
    invoice_period = models.CharField(max_length=100, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    attention = models.CharField(max_length=255, blank=True, default="")
    payment_terms = models.TextField(blank=True, default="")
    narration = models.TextField(blank=True, default="")
    enable_seal_and_sign = models.BooleanField(default=False)
    tax_mode = models.CharField(
        max_length=20, choices=TAX_MODE_CHOICES, default="TAX_EXCLUDED"
    )
    bill_status = models.CharField(
        max_length=20, choices=BILL_STATUS_CHOICES, default="Pending"
    )
    e_invoice_status = models.CharField(
        max_length=20, choices=E_INVOICE_STATUS_CHOICES, default="Draft"
    )
    bank_account = models.ForeignKey(
        "banking.BankAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_invoices",
    )

    total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    tax_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    discount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    product_discount_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    cash_discount_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    paid_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    pending_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    grand_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )

    attachment = models.FileField(
        upload_to="sales_invoices/", null=True, blank=True
    )
    attachment_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = _("Sales Invoice")
        verbose_name_plural = _("Sales Invoices")
        indexes = [
            models.Index(fields=["companyId", "bill_number"]),
            models.Index(fields=["companyId", "date"]),
            models.Index(fields=["companyId", "customer"]),
            models.Index(fields=["companyId", "currency"]),
            models.Index(fields=["companyId", "sales_person"]),
        ]

    def __str__(self) -> str:
        return f"{self.bill_number}"


class SalesInvoiceItem(models.Model):
    """Sales Invoice line item."""

    invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_invoice_items",
    )
    unit = models.ForeignKey(
        "products.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_invoice_items",
    )
    qty = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    rate = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    discount_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    product_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    tax_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0")
    )
    tax_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    si_no = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["si_no", "id"]
        verbose_name = _("Sales Invoice Item")
        verbose_name_plural = _("Sales Invoice Items")

    def __str__(self) -> str:
        return f"{self.invoice.bill_number} - {self.si_no}"
