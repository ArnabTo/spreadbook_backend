import uuid
from django.db import models


CATEGORY_CHOICES = [
    ("purchase", "Purchase"),
    ("sale", "Sale"),
    ("expense", "Expense"),
    ("return", "Return"),
    ("adjustment", "Adjustment"),
]

TYPE_CHOICES = [
    ("in", "In"),
    ("out", "Out"),
]


class InventoryLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    log_type = models.CharField(max_length=10, choices=TYPE_CHOICES, db_index=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reference = models.CharField(max_length=150, blank=True, db_index=True)
    description = models.TextField(blank=True)
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Inventory Log"
        verbose_name_plural = "Inventory Logs"

    def __str__(self):
        return f"{self.get_category_display()} | {self.get_log_type_display()} | {self.reference}"
