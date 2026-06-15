from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.models.common_fields import Timestamp


class SalesReturn(Timestamp):
    TAX_MODE_CHOICES = (
        ("TAX_INCLUDED", _("Tax Included")),
        ("TAX_EXCLUDED", _("Tax Excluded")),
    )
    TYPE_CHOICES = (
        ("CASH", _("Cash")),
        ("CREDIT", _("Credit")),
    )

    companyId = models.ForeignKey(
        "company.Company", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_returns",
    )
    branch = models.ForeignKey(
        "company.Branch", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_returns",
    )
    bill_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_returns",
    )
    currency = models.ForeignKey(
        "sales_quotation.Currency", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_returns",
    )
    currency_rate = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("1"))
    financial_year = models.ForeignKey(
        "financial_years.FinancialYear", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_returns",
    )
    date = models.DateField()
    sales_person = models.ForeignKey(
        "authenticator.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_returns_as_salesperson",
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="CASH")
    si_ref = models.CharField(max_length=100, blank=True, default="")
    narration = models.TextField(blank=True, default="")
    tax_mode = models.CharField(max_length=20, choices=TAX_MODE_CHOICES, default="TAX_EXCLUDED")
    enable_seal_and_sign = models.BooleanField(default=False)
    bank_account = models.ForeignKey(
        "banking.BankAccount", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_returns",
    )

    total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    tax_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    product_discount_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    cash_discount_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    pending_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    grand_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    attachment = models.FileField(upload_to="sales_returns/", null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = _("Sales Return")
        verbose_name_plural = _("Sales Returns")
        indexes = [
            models.Index(fields=["companyId", "bill_number"]),
            models.Index(fields=["companyId", "date"]),
            models.Index(fields=["companyId", "customer"]),
            models.Index(fields=["companyId", "sales_person"]),
            models.Index(fields=["companyId", "currency"]),
            models.Index(fields=["companyId", "bank_account"]),
        ]

    def __str__(self):
        return f"{self.bill_number}"


class SalesReturnItem(models.Model):
    sales_return = models.ForeignKey(
        SalesReturn, on_delete=models.CASCADE, related_name="items",
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_return_items",
    )
    unit = models.ForeignKey(
        "products.Unit", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_return_items",
    )
    qty = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    rate = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    product_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    si_no = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["si_no", "id"]
        verbose_name = _("Sales Return Item")
        verbose_name_plural = _("Sales Return Items")

    def __str__(self):
        return f"{self.sales_return.bill_number} - {self.si_no}"


class SalesReturnPayment(models.Model):
    sales_return = models.ForeignKey(
        SalesReturn, on_delete=models.CASCADE, related_name="payments",
    )
    paying_date = models.DateField()
    paying_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))

    class Meta:
        ordering = ["paying_date", "id"]
        verbose_name = _("Sales Return Payment")
        verbose_name_plural = _("Sales Return Payments")

    def __str__(self):
        return f"{self.sales_return.bill_number} - {self.paying_amount}"
