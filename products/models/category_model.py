from django.db import models
from django.utils.timezone import now


class Category(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_child = models.BooleanField(default=False, help_text="Whether this category is a child/sub-category")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent category (only applicable when is_child=True)",
    )
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    branchId = models.ManyToManyField(
        "company.Branch",
        blank=True,
        help_text="Branches this category is available in",
    )
    is_active = models.BooleanField(default=True, null=True, blank=True)
    created_at = models.DateTimeField(default=now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or "Unnamed Category"
