from django.db import models
from django.utils.timezone import now

from company.models import Branch
from customers.models import Customer
from utils.models.common_fields import Timestamp


class RoomType(Timestamp):
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="hotel_room_types"
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32)
    description = models.TextField(blank=True, null=True)
    base_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_occupancy = models.PositiveIntegerField(default=2)
    amenities = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("branch", "code")
        ordering = ["branch", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Room(Timestamp):
    STATUS_CHOICES = (
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("dirty", "Dirty / Needs Cleaning"),
        ("maintenance", "Maintenance"),
        ("out_of_service", "Out of Service"),
    )

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="hotel_rooms"
    )
    room_type = models.ForeignKey(
        RoomType, on_delete=models.PROTECT, related_name="rooms"
    )
    room_number = models.CharField(max_length=32)
    floor = models.CharField(max_length=32, blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="available"
    )
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("branch", "room_number")
        ordering = ["branch", "room_number"]

    def __str__(self) -> str:
        return f"{self.room_number} - {self.room_type.name}"


class StayReservation(Timestamp):
    STATUS_CHOICES = (
        ("reserved", "Reserved"),
        ("checked_in", "Checked In"),
        ("checked_out", "Checked Out"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    )

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="hotel_reservations"
    )
    guest = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="hotel_stays"
    )
    room_type = models.ForeignKey(
        RoomType, on_delete=models.PROTECT, related_name="reservations"
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reservations",
    )

    check_in_date = models.DateField()
    check_out_date = models.DateField()
    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="reserved")
    source = models.CharField(max_length=60, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    currency = models.CharField(max_length=8, default="BDT")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]

    @property
    def nights(self) -> int:
        if not self.check_in_date or not self.check_out_date:
            return 0
        delta = self.check_out_date - self.check_in_date
        return max(0, delta.days)


class HousekeepingTask(Timestamp):
    TASK_CHOICES = (
        ("clean", "Cleaning"),
        ("inspect", "Inspection"),
        ("linen", "Linen Change"),
        ("maintenance", "Maintenance"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("done", "Done"),
    )

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="hotel_housekeeping_tasks"
    )
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="housekeeping_tasks"
    )
    task_type = models.CharField(max_length=20, choices=TASK_CHOICES, default="clean")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    scheduled_for = models.DateField(default=now)
    completed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]


class Folio(Timestamp):
    STATUS_CHOICES = (
        ("open", "Open"),
        ("closed", "Closed"),
    )

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="hotel_folios"
    )
    reservation = models.OneToOneField(
        StayReservation, on_delete=models.CASCADE, related_name="folio"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    currency = models.CharField(max_length=8, default="BDT")

    class Meta:
        ordering = ["-created_at"]


class FolioLineItem(Timestamp):
    SOURCE_CHOICES = (
        ("room", "Room Charge"),
        ("restaurant", "Restaurant"),
        ("misc", "Misc"),
    )

    folio = models.ForeignKey(Folio, on_delete=models.CASCADE, related_name="items")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="misc")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["created_at"]

    @property
    def amount(self):
        return (self.quantity or 0) * (self.unit_price or 0)
