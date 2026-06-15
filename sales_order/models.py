from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.models.common_fields import Timestamp


class SalesOrder(Timestamp):
    """Sales Order header (company-scoped)."""

    TAX_MODE_CHOICES = (
        ("TAX_INCLUDED", _("Tax Included")),
        ("TAX_EXCLUDED", _("Tax Excluded")),
    )

    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_orders",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_orders",
    )

    bill_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_orders",
    )
    currency = models.ForeignKey(
        "sales_quotation.Currency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_orders",
    )
    currency_rate = models.DecimalField(
        max_digits=18, decimal_places=6, default=Decimal("1")
    )
    financial_year = models.ForeignKey(
        "financial_years.FinancialYear",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_orders",
    )

    date = models.DateField()
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
        related_name="sales_orders_as_salesperson",
    )
    location = models.CharField(max_length=255, blank=True, default="")
    po_ref = models.CharField(max_length=100, blank=True, default="")

    total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    tax_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    product_discount_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    cash_discount_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    grand_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )

    attachment = models.FileField(
        upload_to="sales_orders/", null=True, blank=True
    )
    attachment_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = _("Sales Order")
        verbose_name_plural = _("Sales Orders")
        indexes = [
            models.Index(fields=["companyId", "bill_number"]),
            models.Index(fields=["companyId", "date"]),
            models.Index(fields=["companyId", "customer"]),
            models.Index(fields=["companyId", "currency"]),
            models.Index(fields=["companyId", "sales_person"]),
        ]

    def __str__(self) -> str:
        return f"{self.bill_number}"


class SalesOrderItem(models.Model):
    """Sales Order line item."""

    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    unit = models.ForeignKey(
        "products.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
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
        verbose_name = _("Sales Order Item")
        verbose_name_plural = _("Sales Order Items")

    def __str__(self) -> str:
        return f"{self.order.bill_number} - {self.si_no}"
