from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.models.common_fields import Timestamp


class ProformaInvoice(Timestamp):
    """Proforma Invoice header (company-scoped)."""

    TAX_MODE_CHOICES = (
        ("TAX_INCLUDED", _("Tax Included")),
        ("TAX_EXCLUDED", _("Tax Excluded")),
    )

    TYPE_CHOICES = (
        ("CASH", _("Cash")),
        ("CREDIT", _("Credit")),
    )

    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proforma_invoices",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proforma_invoices",
    )

    bill_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proforma_invoices",
    )
    currency = models.ForeignKey(
        "sales_quotation.Currency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proforma_invoices",
    )
    currency_rate = models.DecimalField(
        max_digits=18, decimal_places=6, default=Decimal("1")
    )
    financial_year = models.ForeignKey(
        "financial_years.FinancialYear",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proforma_invoices",
    )

    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    sales_person = models.ForeignKey(
        "authenticator.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proforma_invoices_as_salesperson",
    )
    type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default="CASH"
    )
    location = models.CharField(max_length=255, blank=True, default="")
    attention = models.CharField(max_length=255, blank=True, default="")
    narration = models.TextField(blank=True, default="")
    tax_mode = models.CharField(
        max_length=20, choices=TAX_MODE_CHOICES, default="TAX_EXCLUDED"
    )
    po_ref = models.CharField(max_length=100, blank=True, default="")
    project_ref_no = models.CharField(max_length=100, blank=True, default="")
    enable_seal_and_sign = models.BooleanField(default=False)

    invoice_period = models.CharField(max_length=100, blank=True, default="")
    supply_date = models.DateField(null=True, blank=True)
    bank_account = models.ForeignKey(
        "banking.BankAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proforma_invoices",
    )
    payment_terms = models.TextField(blank=True, default="")

    total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    tax_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    discount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    grand_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )

    attachment = models.FileField(
        upload_to="proforma_invoices/", null=True, blank=True
    )
    attachment_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = _("Proforma Invoice")
        verbose_name_plural = _("Proforma Invoices")
        indexes = [
            models.Index(fields=["companyId", "bill_number"]),
            models.Index(fields=["companyId", "date"]),
            models.Index(fields=["companyId", "customer"]),
            models.Index(fields=["companyId", "currency"]),
            models.Index(fields=["companyId", "sales_person"]),
            models.Index(fields=["companyId", "due_date"]),
            models.Index(fields=["companyId", "bank_account"]),
        ]

    def __str__(self) -> str:
        return f"{self.bill_number}"


class ProformaInvoiceItem(models.Model):
    """Proforma Invoice line item."""

    invoice = models.ForeignKey(
        ProformaInvoice,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proforma_invoice_items",
    )
    unit = models.ForeignKey(
        "products.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proforma_invoice_items",
    )
    qty = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    rate = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0")
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
        verbose_name = _("Proforma Invoice Item")
        verbose_name_plural = _("Proforma Invoice Items")

    def __str__(self) -> str:
        return f"{self.invoice.bill_number} - {self.si_no}"
