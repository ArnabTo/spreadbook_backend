from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.models.common_fields import Timestamp


class BankAccount(Timestamp):
    """Bank Account master scoped per company."""

    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bank_accounts",
    )
    name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100, blank=True, default="")
    bank_name = models.CharField(max_length=255, blank=True, default="")
    branch_name = models.CharField(max_length=255, blank=True, default="")
    iban = models.CharField(max_length=100, blank=True, default="")
    swift_code = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Bank Account")
        verbose_name_plural = _("Bank Accounts")

    def __str__(self) -> str:
        if self.account_number:
            return f"{self.name} - {self.account_number}"
        return self.name
