import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Simple per-user in-app notification."""

    class Type(models.TextChoices):
        ORDER = "order", "order"
        KITCHEN = "kitchen", "kitchen"
        INVENTORY = "inventory", "inventory"
        PAYMENT = "payment", "payment"
        BOOKING = "booking", "booking"
        STAFF = "staff", "staff"
        SYSTEM = "system", "system"
        SUCCESS = "success", "success"
        WARNING = "warning", "warning"
        ERROR = "error", "error"

    class Priority(models.TextChoices):
        LOW = "low", "low"
        MEDIUM = "medium", "medium"
        HIGH = "high", "high"
        URGENT = "urgent", "urgent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, default="")
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )

    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    actionUrl = models.CharField(max_length=200, null=True, blank=True)
    actionLabel = models.CharField(max_length=100, null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)

    # Prevent spam: allow creating a "same" reminder only once.
    dedupe_key = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "read", "-created_at"]),
            models.Index(fields=["company", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"],
                name="uniq_notification_user_dedupe_key",
                condition=models.Q(dedupe_key__isnull=False),
            )
        ]

    def __str__(self) -> str:
        return f"{self.type}: {self.title}"
