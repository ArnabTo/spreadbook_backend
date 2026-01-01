import uuid

from django.conf import settings
from django.db import models
from django.utils.timezone import now


def prescription_upload_to(instance, filename: str) -> str:
    return f"assets/uploads/pharmacy/prescriptions/{instance.id}/{filename}"


PRESCRIPTION_STATUS_CHOICES = (
    ("draft", "Draft"),
    ("submitted", "Submitted"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
    ("expired", "Expired"),
)


class Prescription(models.Model):
    """Prescription record for pharmacy sales.

    This is backend-first and UI-safe: enforcement is feature-flagged per company.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenant scoping
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions",
    )

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_prescriptions",
    )

    status = models.CharField(
        max_length=20,
        choices=PRESCRIPTION_STATUS_CHOICES,
        default="draft",
        db_index=True,
    )

    issued_date = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    doctor_name = models.CharField(max_length=200, null=True, blank=True)
    doctor_registration_no = models.CharField(max_length=100, null=True, blank=True)
    clinic_name = models.CharField(max_length=200, null=True, blank=True)

    notes = models.TextField(null=True, blank=True)

    attachment = models.FileField(
        upload_to=prescription_upload_to,
        null=True,
        blank=True,
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_prescriptions",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_prescriptions",
    )
    rejection_reason = models.TextField(null=True, blank=True)

    createdAt = models.DateTimeField(auto_now_add=True)
    updateAt = models.DateTimeField(auto_now=True)

    def mark_submitted(self):
        if self.status not in {"draft", "rejected"}:
            return
        self.status = "submitted"
        self.submitted_at = now()

    def mark_approved(self, *, user=None):
        self.status = "approved"
        self.approved_at = now()
        if user is not None:
            self.approved_by = user

    def mark_rejected(self, *, user=None, reason: str | None = None):
        self.status = "rejected"
        self.rejected_at = now()
        if user is not None:
            self.rejected_by = user
        if reason is not None:
            self.rejection_reason = reason

    def __str__(self):
        return f"Prescription {str(self.id)[:8]} ({self.status})"

    class Meta:
        ordering = ["-createdAt"]


class PrescriptionItem(models.Model):
    """Line items for a prescription (optional).

    Useful for validation/reporting; not strictly required for enforcement.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    prescription = models.ForeignKey(
        Prescription, related_name="items", on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescription_items",
    )

    product_name = models.CharField(max_length=200, null=True, blank=True)
    product_sku = models.CharField(max_length=100, null=True, blank=True)

    quantity_prescribed = models.PositiveIntegerField(default=1)
    dosage_instructions = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.product and not self.product_name:
            self.product_name = getattr(self.product, "name", None)
        if self.product and not self.product_sku:
            self.product_sku = getattr(self.product, "sku", None)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity_prescribed}x {self.product_name or 'Item'}"
