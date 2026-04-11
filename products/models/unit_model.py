from django.db import models
from company.models import Company


class Unit(models.Model):
    companyId = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="units",
    )
    name = models.CharField(max_length=100, default="Taka")
    status = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["companyId", "name"], name="uniq_unit_company_name"
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        """String for representing the Model object."""
        return self.name
