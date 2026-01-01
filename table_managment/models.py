import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Table(models.Model):
    """
    Model representing a restaurant table
    """

    STATUS_CHOICES = [
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("reserved", "Reserved"),
        ("maintenance", "Under Maintenance"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenant scoping
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    number = models.PositiveIntegerField(unique=True, validators=[MinValueValidator(1)])
    seats = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="available"
    )

    # Location information
    section = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Table section (e.g., Dining Room, Patio)",
    )
    floor = models.CharField(
        max_length=20, blank=True, null=True, default="Ground Floor"
    )

    # Table characteristics
    is_active = models.BooleanField(default=True)
    table_type = models.CharField(
        max_length=30, blank=True, null=True, help_text="e.g., Regular, VIP, Booth"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["number"]
        verbose_name = "Table"
        verbose_name_plural = "Tables"

    def __str__(self):
        return f"Table {self.number} ({self.seats} seats)"

    @property
    def current_occupation(self):
        """Get current table occupation if exists"""
        return self.occupations.filter(end_time__isnull=True).first()

    @property
    def current_reservation(self):
        """Get active reservation if exists"""
        now = timezone.now()
        return self.reservations.filter(
            reservation_time__lte=now,
            reservation_time__gte=now - timezone.timedelta(hours=2),
            status="confirmed",
        ).first()

    @property
    def is_occupied(self):
        """Check if table is currently occupied"""
        return self.current_occupation is not None

    @property
    def is_reserved(self):
        """Check if table has active reservation"""
        return self.current_reservation is not None


class TableOccupation(models.Model):
    """
    Model to track table occupations
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(
        Table, on_delete=models.CASCADE, related_name="occupations"
    )

    # Customer information
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    party_size = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    # Staff assignment
    waiter = models.CharField(max_length=100, blank=True, null=True)

    # Timing
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    # Order information
    order_amount = models.FloatField(default=0.0, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_time"]
        verbose_name = "Table Occupation"
        verbose_name_plural = "Table Occupations"

    def __str__(self):
        return (
            f"Table {self.table.number} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
        )

    @property
    def duration(self):
        """Calculate occupation duration"""
        end_time = self.end_time or timezone.now()
        duration = end_time - self.start_time

        total_minutes = int(duration.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def end_occupation(self, final_amount=None):
        """End the table occupation"""
        self.end_time = timezone.now()
        if final_amount is not None:
            self.order_amount = final_amount
        self.is_active = False
        self.save()

        # Update table status
        self.table.status = "available"
        self.table.save()


class TableReservation(models.Model):
    """
    Model for table reservations
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
        ("no_show", "No Show"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(
        Table, on_delete=models.CASCADE, related_name="reservations"
    )

    # Customer information
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True, null=True)
    party_size = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    # Reservation details
    reservation_time = models.DateTimeField()
    duration_hours = models.FloatField(
        default=2.0, validators=[MinValueValidator(0.5), MaxValueValidator(6.0)]
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Special requirements
    special_requests = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["reservation_time"]
        verbose_name = "Table Reservation"
        verbose_name_plural = "Table Reservations"

    def __str__(self):
        return f"Table {self.table.number} - {self.customer_name} ({self.reservation_time.strftime('%Y-%m-%d %H:%M')})"

    @property
    def is_active(self):
        """Check if reservation is currently active"""
        now = timezone.now()
        end_time = self.reservation_time + timezone.timedelta(hours=self.duration_hours)
        return self.status == "confirmed" and self.reservation_time <= now <= end_time

    def mark_as_arrived(self, waiter=None):
        """Mark reservation as arrived and create occupation"""
        if self.status != "confirmed":
            raise ValueError("Can only mark confirmed reservations as arrived")

        # Create table occupation
        occupation = TableOccupation.objects.create(
            table=self.table,
            customer_name=self.customer_name,
            customer_phone=self.customer_phone,
            party_size=self.party_size,
            waiter=waiter,
            notes=f"Reservation: {self.special_requests or ''}",
        )

        # Update table status
        self.table.status = "occupied"
        self.table.save()

        # Update reservation status
        self.status = "completed"
        self.save()

        return occupation
