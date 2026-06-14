from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.models.common_fields import Timestamp


class Currency(Timestamp):
    """Currency master scoped per company."""

    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="currencies",
    )
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10, blank=True, default="")
    exchange_rate = models.DecimalField(
        max_digits=18, decimal_places=6, default=Decimal("1")
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = _("Currency")
        verbose_name_plural = _("Currencies")

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class SalesQuotation(Timestamp):
    """Sales Quotation header (company-scoped)."""

    TAX_MODE_CHOICES = (
        ("TAX_INCLUDED", _("Tax Included")),
        ("TAX_EXCLUDED", _("Tax Excluded")),
    )

    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotations",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotations",
    )

    bill_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotations",
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotations",
    )
    financial_year = models.ForeignKey(
        "financial_years.FinancialYear",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotations",
    )

    quotation_validity = models.DateField(null=True, blank=True)
    subject = models.CharField(max_length=255, blank=True, default="")
    show_last_quotation_price = models.BooleanField(default=False)
    bank_account = models.ForeignKey(
        "banking.BankAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotations",
    )
    show_total_box_quotation = models.BooleanField(default=False)
    date = models.DateField()
    rfq_ref = models.CharField(max_length=100, blank=True, default="")
    currency_rate = models.DecimalField(
        max_digits=18, decimal_places=6, default=Decimal("1")
    )
    payment_terms = models.TextField(blank=True, default="")
    contact_details = models.TextField(blank=True, default="")
    site_name = models.CharField(max_length=255, blank=True, default="")
    enable_seal_and_sign = models.BooleanField(default=False)
    narration = models.TextField(blank=True, default="")
    tax_mode = models.CharField(
        max_length=20, choices=TAX_MODE_CHOICES, default="TAX_EXCLUDED"
    )
    attention = models.CharField(max_length=255, blank=True, default="")
    sales_person = models.ForeignKey(
        "authenticator.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotations_as_salesperson",
    )
    ref_date = models.DateField(null=True, blank=True)

    total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    tax_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    discount_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    grand_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )

    attachment = models.FileField(
        upload_to="sales_quotations/", null=True, blank=True
    )
    attachment_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = _("Sales Quotation")
        verbose_name_plural = _("Sales Quotations")
        indexes = [
            models.Index(fields=["companyId", "bill_number"]),
            models.Index(fields=["companyId", "date"]),
            models.Index(fields=["companyId", "customer"]),
            models.Index(fields=["companyId", "currency"]),
            models.Index(fields=["companyId", "sales_person"]),
        ]

    def __str__(self) -> str:
        return f"{self.bill_number}"


class SalesQuotationItem(models.Model):
    """Sales Quotation line item."""

    quotation = models.ForeignKey(
        SalesQuotation,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotation_items",
    )
    unit = models.ForeignKey(
        "products.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotation_items",
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
        verbose_name = _("Sales Quotation Item")
        verbose_name_plural = _("Sales Quotation Items")

    def __str__(self) -> str:
        return f"{self.quotation.bill_number} - {self.si_no}"
