from django.db.models import Q
from rest_framework import serializers

from .models import (
    RoomType,
    Room,
    StayReservation,
    HousekeepingTask,
    Folio,
    FolioLineItem,
)


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = "__all__"


class RoomSerializer(serializers.ModelSerializer):
    room_type_name = serializers.CharField(source="room_type.name", read_only=True)

    class Meta:
        model = Room
        fields = "__all__"


class StayReservationSerializer(serializers.ModelSerializer):
    guest_name = serializers.CharField(source="guest.name", read_only=True)
    room_number = serializers.CharField(source="room.room_number", read_only=True)
    nights = serializers.IntegerField(read_only=True)

    class Meta:
        model = StayReservation
        fields = "__all__"

    def validate(self, attrs):
        instance: StayReservation | None = getattr(self, "instance", None)

        check_in_date = attrs.get("check_in_date") or (
            instance.check_in_date if instance else None
        )
        check_out_date = attrs.get("check_out_date") or (
            instance.check_out_date if instance else None
        )
        if check_in_date and check_out_date and check_out_date <= check_in_date:
            raise serializers.ValidationError(
                {"check_out_date": "Check-out date must be after check-in date."}
            )

        adults = (
            attrs.get("adults")
            if "adults" in attrs
            else (instance.adults if instance else None)
        )
        children = (
            attrs.get("children")
            if "children" in attrs
            else (instance.children if instance else None)
        )
        if adults is not None and adults < 1:
            raise serializers.ValidationError({"adults": "Adults must be at least 1."})
        if children is not None and children < 0:
            raise serializers.ValidationError(
                {"children": "Children cannot be negative."}
            )

        branch_id = attrs.get("branch_id") or (instance.branch_id if instance else None)
        room = (
            attrs.get("room")
            if "room" in attrs
            else (instance.room if instance else None)
        )
        room_type_id = attrs.get("room_type_id") or (
            instance.room_type_id if instance else None
        )

        if room is not None:
            if branch_id and room.branch_id != branch_id:
                raise serializers.ValidationError(
                    {"room": "Room must belong to the same branch."}
                )
            if room_type_id and room.room_type_id != room_type_id:
                raise serializers.ValidationError(
                    {"room": "Selected room does not match selected room type."}
                )

        # Prevent overlapping stays for the same room (for active stays)
        if room is not None and check_in_date and check_out_date:
            active_statuses = ["reserved", "checked_in"]
            qs = StayReservation.objects.filter(room=room, status__in=active_statuses)
            if instance is not None:
                qs = qs.exclude(pk=instance.pk)
            qs = qs.filter(
                Q(check_in_date__lt=check_out_date)
                & Q(check_out_date__gt=check_in_date)
            )
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "room": "Room already has an overlapping reservation for the selected dates."
                    }
                )

        return attrs


class HousekeepingTaskSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source="room.room_number", read_only=True)

    class Meta:
        model = HousekeepingTask
        fields = "__all__"


class FolioLineItemSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = FolioLineItem
        fields = "__all__"


class FolioSerializer(serializers.ModelSerializer):
    items = FolioLineItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    reservation_guest_name = serializers.CharField(
        source="reservation.guest.name", read_only=True
    )
    reservation_status = serializers.CharField(
        source="reservation.status", read_only=True
    )

    class Meta:
        model = Folio
        fields = "__all__"

    def get_total_amount(self, obj: Folio):
        try:
            items = obj.items.all()
        except Exception:
            items = []

        total = 0.0
        for item in items:
            try:
                total += float(item.amount)
            except Exception:
                continue

        return f"{total:.2f}"
