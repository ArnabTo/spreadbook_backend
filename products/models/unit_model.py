from django.db import models
from django.core.exceptions import ValidationError
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
    short_name = models.CharField(max_length=50, blank=True, null=True)
    arabic_name = models.CharField(max_length=100, blank=True, null=True)
    is_child = models.BooleanField(default=False)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_units",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
    )
    status = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["companyId", "name"], name="uniq_unit_company_name"
            ),
        ]
        ordering = ["name"]

    def clean(self):
        if self.is_child:
            if not self.parent:
                raise ValidationError({"parent": "Parent unit is required when Is Child is true."})
            if self.quantity is None:
                raise ValidationError({"quantity": "Quantity is required when Is Child is true."})
            if self.quantity is not None and self.quantity <= 0:
                raise ValidationError({"quantity": "Quantity must be greater than 0."})
            if self.parent == self:
                raise ValidationError({"parent": "A unit cannot be its own parent."})
        else:
            if self.parent is not None:
                raise ValidationError({"parent": "Parent must be null when Is Child is false."})
            if self.quantity is not None:
                raise ValidationError({"quantity": "Quantity must be null when Is Child is false."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
