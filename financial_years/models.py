from django.db import models
from django.core.exceptions import ValidationError
from utils.models.common_fields import Timestamp


class FinancialYear(Timestamp):
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="financial_years",
    )
    name = models.CharField(max_length=255)
    from_date = models.DateField()
    to_date = models.DateField()
    closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-from_date"]
        verbose_name = "Financial Year"
        verbose_name_plural = "Financial Years"
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["name"]),
            models.Index(fields=["from_date"]),
            models.Index(fields=["to_date"]),
            models.Index(fields=["closed"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_company_fy_name",
            ),
        ]

    def clean(self):
        if self.from_date and self.to_date and self.from_date >= self.to_date:
            raise ValidationError("From Date must be earlier than To Date.")

        if self.company_id and self.from_date and self.to_date:
            overlapping = (
                FinancialYear.objects.filter(
                    company_id=self.company_id,
                    from_date__lt=self.to_date,
                    to_date__gt=self.from_date,
                )
                .exclude(pk=self.pk)
                .exists()
            )
            if overlapping:
                raise ValidationError(
                    "Financial year overlaps with an existing financial year."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.from_date} → {self.to_date})"
