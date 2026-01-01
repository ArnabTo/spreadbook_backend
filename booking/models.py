from django.db import models
from django.utils import timezone
import uuid


class Booking(models.Model):
    """Restaurant booking model matching frontend interface"""

    STATUS_CHOICES = [
        ("confirmed", "Confirmed"),
        ("pending", "Pending"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_name = models.CharField(max_length=200, verbose_name="Customer Name")
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    date = models.DateField()
    time = models.TimeField()
    guests = models.PositiveIntegerField()
    table = models.CharField(max_length=50, help_text="Table identifier or number")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True, null=True)

    # Additional fields for better management
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "time"]
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"

    def __str__(self):
        return f"{self.customer_name} - {self.date} {self.time} ({self.guests} guests)"

    @property
    def is_upcoming(self):
        """Check if booking is in the future"""
        booking_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.time)
        )
        return booking_datetime > timezone.now()

    @property
    def formatted_datetime(self):
        """Return formatted date and time string"""
        return f"{self.date.strftime('%B %d, %Y')} at {self.time.strftime('%I:%M %p')}"
