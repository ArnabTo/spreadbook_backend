from django.db.models import Q
from rest_framework import serializers

from .models import (
    UnitType,
    Unit,
    ResortReservation,
    HousekeepingTask,
    MaintenanceTicket,
    Activity,
    Package,
    Folio,
    FolioLineItem,
)


class UnitTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitType
        fields = "__all__"


class UnitSerializer(serializers.ModelSerializer):
    unit_type_name = serializers.CharField(source="unit_type.name", read_only=True)

    class Meta:
        model = Unit
        fields = "__all__"


class ResortReservationSerializer(serializers.ModelSerializer):
    guest_name = serializers.CharField(source="guest.name", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True)
    nights = serializers.IntegerField(read_only=True)

    class Meta:
        model = ResortReservation
        fields = "__all__"

    def validate(self, attrs):
        instance: ResortReservation | None = getattr(self, "instance", None)

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
        unit = (
            attrs.get("unit")
            if "unit" in attrs
            else (instance.unit if instance else None)
        )
        unit_type_id = attrs.get("unit_type_id") or (
            instance.unit_type_id if instance else None
        )

        if unit is not None:
            if branch_id and unit.branch_id != branch_id:
                raise serializers.ValidationError(
                    {"unit": "Unit must belong to the same branch."}
                )
            if unit_type_id and unit.unit_type_id != unit_type_id:
                raise serializers.ValidationError(
                    {"unit": "Selected unit does not match selected unit type."}
                )

        # Prevent overlapping stays for the same unit (for active stays)
        if unit is not None and check_in_date and check_out_date:
            active_statuses = ["reserved", "checked_in"]
            qs = ResortReservation.objects.filter(unit=unit, status__in=active_statuses)
            if instance is not None:
                qs = qs.exclude(pk=instance.pk)
            qs = qs.filter(
                Q(check_in_date__lt=check_out_date)
                & Q(check_out_date__gt=check_in_date)
            )
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "unit": "Unit already has an overlapping reservation for the selected dates."
                    }
                )

        return attrs


class HousekeepingTaskSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True)

    class Meta:
        model = HousekeepingTask
        fields = "__all__"


class MaintenanceTicketSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True)

    class Meta:
        model = MaintenanceTicket
        fields = "__all__"


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = "__all__"


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
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
