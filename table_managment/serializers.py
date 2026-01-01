from rest_framework import serializers
from django.utils import timezone
from .models import Table, TableOccupation, TableReservation


class TableSerializer(serializers.ModelSerializer):
    """
    Serializer for Table model
    """

    # Read-only calculated fields
    current_waiter = serializers.SerializerMethodField()
    time_occupied = serializers.SerializerMethodField()
    order_amount = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    party_size = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = [
            "id",
            "companyId",
            "branch",
            "number",
            "seats",
            "status",
            "section",
            "floor",
            "table_type",
            "is_active",
            "current_waiter",
            "time_occupied",
            "order_amount",
            "customer_name",
            "party_size",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "companyId", "created_at", "updated_at"]

    def validate_number(self, value):
        """Validate table number"""
        if value is None or value < 1:
            raise serializers.ValidationError("Table number must be a positive integer")

        # Check for uniqueness during creation
        if not self.instance:  # Creating new table
            if Table.objects.filter(number=value).exists():
                raise serializers.ValidationError(
                    f"Table number {value} already exists"
                )
        else:  # Updating existing table
            # Allow keeping the same number for updates
            if Table.objects.filter(number=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(
                    f"Table number {value} already exists"
                )

        return value

    def validate_seats(self, value):
        """Validate number of seats"""
        if value is None or value < 1 or value > 20:
            raise serializers.ValidationError(
                "Number of seats must be between 1 and 20"
            )
        return value

    def get_current_waiter(self, obj):
        """Get current waiter if table is occupied"""
        occupation = obj.current_occupation
        return occupation.waiter if occupation else None

    def get_time_occupied(self, obj):
        """Get occupation duration"""
        occupation = obj.current_occupation
        if occupation:
            return occupation.duration

        # Check for active reservation
        reservation = obj.current_reservation
        if reservation:
            return reservation.reservation_time.strftime("%I:%M %p")

        return None

    def get_order_amount(self, obj):
        """Get current order amount"""
        occupation = obj.current_occupation
        return occupation.order_amount if occupation else 0.0

    def get_customer_name(self, obj):
        """Get current customer name"""
        occupation = obj.current_occupation
        if occupation and occupation.customer_name:
            return occupation.customer_name

        # Check for active reservation
        reservation = obj.current_reservation
        return reservation.customer_name if reservation else None

    def get_party_size(self, obj):
        """Get current party size"""
        occupation = obj.current_occupation
        if occupation:
            return occupation.party_size

        # Check for active reservation
        reservation = obj.current_reservation
        return reservation.party_size if reservation else None


class TableOccupationSerializer(serializers.ModelSerializer):
    """
    Serializer for TableOccupation model
    """

    table_number = serializers.IntegerField(source="table.number", read_only=True)
    duration = serializers.ReadOnlyField()

    class Meta:
        model = TableOccupation
        fields = [
            "id",
            "table",
            "table_number",
            "customer_name",
            "customer_phone",
            "party_size",
            "waiter",
            "start_time",
            "end_time",
            "duration",
            "order_amount",
            "notes",
            "is_active",
        ]
        read_only_fields = ["id", "start_time", "duration", "table_number"]

    def validate_table(self, value):
        """Ensure table is available for occupation"""
        if hasattr(self, "instance") and self.instance:
            # Allow updates to existing occupations
            return value

        if value.status != "available":
            raise serializers.ValidationError(
                f"Table {value.number} is not available for occupation"
            )
        return value

    def create(self, validated_data):
        """Create occupation and update table status"""
        table = validated_data["table"]
        occupation = super().create(validated_data)

        # Update table status
        table.status = "occupied"
        table.save()

        return occupation


class TableReservationSerializer(serializers.ModelSerializer):
    """
    Serializer for TableReservation model
    """

    table_number = serializers.IntegerField(source="table.number", read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = TableReservation
        fields = [
            "id",
            "table",
            "table_number",
            "customer_name",
            "customer_phone",
            "customer_email",
            "party_size",
            "reservation_time",
            "duration_hours",
            "status",
            "special_requests",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "table_number",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate_reservation_time(self, value):
        """Ensure reservation is not in the past"""
        if value < timezone.now():
            raise serializers.ValidationError("Reservation time cannot be in the past")
        return value

    def validate_party_size(self, value):
        """Validate party size against table capacity"""
        table = (
            self.initial_data.get("table") if hasattr(self, "initial_data") else None
        )
        if hasattr(self, "instance") and self.instance:
            table = table or self.instance.table

        if table and isinstance(table, str):
            # Handle table ID as string
            from .models import Table

            try:
                table = Table.objects.get(id=table)
            except Table.DoesNotExist:
                raise serializers.ValidationError("Invalid table selected")

        if table and value > table.seats:
            raise serializers.ValidationError(
                f"Party size ({value}) exceeds table capacity ({table.seats})"
            )
        return value

    def create(self, validated_data):
        """Create reservation and update table status if confirmed"""
        reservation = super().create(validated_data)

        # If confirmed reservation, update table status
        if reservation.status == "confirmed":
            table = reservation.table
            table.status = "reserved"
            table.save()

        return reservation


class AssignTableSerializer(serializers.Serializer):
    """
    Serializer for assigning a table
    """

    customer_name = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    customer_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    party_size = serializers.IntegerField(min_value=1)
    waiter = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_party_size(self, value):
        """Validate party size against table capacity"""
        table_id = self.context.get("table_id")
        if table_id:
            try:
                table = Table.objects.get(id=table_id)
                if value > table.seats:
                    raise serializers.ValidationError(
                        f"Party size ({value}) exceeds table capacity ({table.seats})"
                    )
            except Table.DoesNotExist:
                raise serializers.ValidationError("Invalid table")
        return value


class ClearTableSerializer(serializers.Serializer):
    """
    Serializer for clearing a table
    """

    final_amount = serializers.FloatField(required=False, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)


class TableStatsSerializer(serializers.Serializer):
    """
    Serializer for table statistics
    """

    total_tables = serializers.IntegerField()
    available_tables = serializers.IntegerField()
    occupied_tables = serializers.IntegerField()
    reserved_tables = serializers.IntegerField()
    maintenance_tables = serializers.IntegerField()

    total_seats = serializers.IntegerField()
    occupied_seats = serializers.IntegerField()
    occupancy_rate = serializers.FloatField()

    avg_occupation_time = serializers.CharField()
    total_revenue_today = serializers.FloatField()
    active_occupations = serializers.IntegerField()
    upcoming_reservations = serializers.IntegerField()


class BulkTableUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk table operations
    """

    table_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=50
    )
    action = serializers.ChoiceField(
        choices=[
            ("mark_available", "Mark Available"),
            ("mark_maintenance", "Mark Under Maintenance"),
            ("clear_tables", "Clear Tables"),
        ]
    )

    def validate_table_ids(self, value):
        """Ensure all table IDs exist"""
        existing_ids = set(
            Table.objects.filter(id__in=value).values_list("id", flat=True)
        )
        provided_ids = set(value)

        if existing_ids != provided_ids:
            missing_ids = provided_ids - existing_ids
            raise serializers.ValidationError(
                f"Tables with IDs {list(missing_ids)} do not exist"
            )
        return value
