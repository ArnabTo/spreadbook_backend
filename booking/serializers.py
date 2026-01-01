from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for Booking model matching frontend interface"""

    # Custom field names to match frontend interface
    customerName = serializers.CharField(source="customer_name")

    # Read-only fields for additional info
    formatted_datetime = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()
    updated_at = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "customerName",
            "phone",
            "email",
            "date",
            "time",
            "guests",
            "table",
            "status",
            "notes",
            "formatted_datetime",
            "is_upcoming",
            "created_at",
            "updated_at",
        ]

    def validate_guests(self, value):
        """Validate number of guests"""
        if value <= 0:
            raise serializers.ValidationError(
                "Number of guests must be greater than 0."
            )
        if value > 20:  # Assuming max 20 guests per booking
            raise serializers.ValidationError("Maximum 20 guests allowed per booking.")
        return value

    def validate_phone(self, value):
        """Validate phone number"""
        if not value.strip():
            raise serializers.ValidationError("Phone number is required.")
        return value

    def validate(self, data):
        """Custom validation for booking"""
        date = data.get("date")
        time = data.get("time")

        if date and time:
            # Check if booking is not in the past
            import datetime
            from django.utils import timezone

            booking_datetime = timezone.make_aware(
                datetime.datetime.combine(date, time)
            )

            if booking_datetime <= timezone.now():
                raise serializers.ValidationError(
                    "Booking cannot be made for past date/time."
                )

        return data


class BookingListSerializer(serializers.ModelSerializer):
    """Simplified serializer for booking list views"""

    customerName = serializers.CharField(source="customer_name")
    formatted_datetime = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "customerName",
            "phone",
            "date",
            "time",
            "guests",
            "table",
            "status",
            "formatted_datetime",
            "is_upcoming",
        ]


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer specifically for creating bookings"""

    customerName = serializers.CharField(source="customer_name")

    class Meta:
        model = Booking
        fields = [
            "customerName",
            "phone",
            "email",
            "date",
            "time",
            "guests",
            "table",
            "status",
            "notes",
        ]

    def validate_guests(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Number of guests must be greater than 0."
            )
        if value > 20:
            raise serializers.ValidationError("Maximum 20 guests allowed per booking.")
        return value
