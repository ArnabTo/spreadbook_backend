from django.db import models
from django.utils.timezone import now


class SystemSettings(models.Model):
    """
    Company- and optionally branch-scoped system settings.
    When branch is None the record acts as the company-level default.
    When branch is set it overrides the company default for that branch.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="system_settings",
        help_text="Company this settings record belongs to",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="system_settings",
        help_text="Leave blank for company-level default; set to override per branch",
    )

    # ── General Settings ─────────────────────────────────────────────────────
    restaurant_name = models.CharField(
        max_length=200, blank=True, default="Restaurant MS")
    currency = models.CharField(max_length=10, blank=True, default="USD")
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00)
    multi_branch_mode = models.BooleanField(default=True)
    sound_enabled = models.BooleanField(default=True)
    allow_out_of_stock_orders = models.BooleanField(default=False)
    allow_pos_price_change = models.BooleanField(default=False)
    allow_pos_partial_cash_payment = models.BooleanField(default=False)
    quick_purchase_enabled = models.BooleanField(default=False)

    # ── Thermal Printer ───────────────────────────────────────────────────────
    thermal_printer_url = models.CharField(
        max_length=255, blank=True, default="http://localhost:8000")
    thermal_printer_name = models.CharField(
        max_length=255, blank=True, default="RONGTA 80mm Series Printer")

    # ── Security Settings ─────────────────────────────────────────────────────
    two_factor_auth = models.BooleanField(default=False)
    session_timeout = models.IntegerField(
        default=30, help_text="Minutes before auto-logout")
    password_expiry_days = models.IntegerField(
        default=90, help_text="0 means never")

    # ── Notification Settings ─────────────────────────────────────────────────
    low_stock_alerts = models.BooleanField(default=True)
    daily_sales_report = models.BooleanField(default=True)
    new_order_notifications = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=False)

    # ── Meta ──────────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("company", "branch")]
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"
        ordering = ["company", "branch"]

    def __str__(self):
        if self.branch:
            return f"{self.company} / {self.branch} – settings"
        return f"{self.company} – settings (company default)"
