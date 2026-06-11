from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.models.common_fields import Timestamp
from account_groups.models import AccountGroup
import uuid


class Account(Timestamp):
    """Ledger Account model with banking and bilingual address fields"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenant scoping
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_accounts",
    )

    # Account Info
    parent = models.ForeignKey(
        AccountGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ledger_accounts",
        verbose_name=_("Parent"),
    )
    display_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Display Name"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))
    mailing_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Mailing Name"))
    arabic_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Arabic Name"))

    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("Phone Number"))
    mobile_number = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("Mobile Number"))

    # Banking
    bank_name = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name=_("Bank Name"))
    arabic_bank_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Arabic Bank Name"))
    bank_account_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Bank Account Number"))
    iban_no = models.CharField(max_length=50, blank=True, null=True, db_index=True, verbose_name=_("IBAN No"))
    branch_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Branch Name"))
    branch_code = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Branch Code"))
    swift_code = models.CharField(max_length=20, blank=True, null=True, db_index=True, verbose_name=_("Swift Code"))

    email = models.EmailField(db_index=True, blank=True, null=True, verbose_name=_("Email"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    # Accounting
    opening_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name=_("Opening Balance"), db_index=True
    )
    is_debit = models.BooleanField(default=False, verbose_name=_("Is Debit"))
    cheque_print_enabled = models.BooleanField(default=False, verbose_name=_("Cheque Print Enabled"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    # Bilingual Address Fields
    country_ref = models.ForeignKey(
        "company.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_account_countries",
    )
    arabic_country = models.CharField(max_length=100, blank=True, null=True)
    state_ref = models.ForeignKey(
        "company.StateProvince",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_account_states",
    )
    arabic_state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, default="", blank=True, null=True)
    arabic_city = models.CharField(max_length=100, blank=True, null=True)
    building_no = models.CharField(max_length=50, blank=True, null=True)
    arabic_building_no = models.CharField(max_length=50, blank=True, null=True)
    street_name = models.CharField(max_length=200, blank=True, null=True)
    arabic_street_name = models.CharField(max_length=200, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    arabic_district = models.CharField(max_length=100, blank=True, null=True)
    additional_no = models.CharField(max_length=50, blank=True, null=True)
    arabic_additional_no = models.CharField(max_length=50, blank=True, null=True)
    zip_code = models.CharField(max_length=200, blank=True, null=True)
    arabic_zip_code = models.CharField(max_length=20, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.cheque_print_enabled is not False:
            self.cheque_print_enabled = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.bank_name or 'No Bank'})"

    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ["-created_at", "name"]
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["name"]),
            models.Index(fields=["bank_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["iban_no"]),
            models.Index(fields=["swift_code"]),
            models.Index(fields=["opening_balance"]),
            models.Index(fields=["country_ref"]),
            models.Index(fields=["state_ref"]),
        ]
