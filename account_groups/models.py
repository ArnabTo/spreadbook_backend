from django.db import models
from utils.models.common_fields import Timestamp


class AccountGroupParent(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Account Group Parent"
        verbose_name_plural = "Account Group Parents"

    def __str__(self):
        return self.name


class AccountGroup(Timestamp):
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="account_groups",
    )
    name = models.CharField(max_length=255)
    account_code = models.CharField(max_length=100)
    parent = models.ForeignKey(
        AccountGroupParent,
        on_delete=models.PROTECT,
        related_name="account_groups",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Account Group"
        verbose_name_plural = "Account Groups"
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["name"]),
            models.Index(fields=["account_code"]),
            models.Index(fields=["parent"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "account_code"],
                name="unique_company_account_code",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.account_code})"
