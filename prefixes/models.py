from django.db import models
from django.core.exceptions import ValidationError
from utils.models.common_fields import Timestamp


class Prefix(Timestamp):
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="prefixes",
    )

    type = models.CharField(max_length=100)
    prefix = models.CharField(max_length=100)
    separator = models.CharField(max_length=10, default="-")
    start_index = models.PositiveIntegerField(default=0)
    current_index = models.PositiveIntegerField(default=0)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    financial_year = models.ForeignKey(
        "financial_years.FinancialYear",
        on_delete=models.PROTECT,
        related_name="prefixes",
    )
    narration = models.TextField(blank=True, default="")
    prefix_series = models.CharField(max_length=100, blank=True, default="")
    applicable = models.BooleanField(default=True)
    exclude_tax = models.BooleanField(default=False)

    extra_config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Prefix"
        verbose_name_plural = "Prefixes"
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["type"]),
            models.Index(fields=["prefix"]),
            models.Index(fields=["financial_year"]),
            models.Index(fields=["applicable"]),
        ]

    def clean(self):
        if self.from_date and self.to_date and self.from_date >= self.to_date:
            raise ValidationError("From Date must be earlier than To Date.")

        if self.current_index < self.start_index:
            raise ValidationError("Current Index must be >= Start Index.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prefix} ({self.type})"
