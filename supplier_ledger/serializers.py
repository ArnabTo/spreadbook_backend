from decimal import Decimal
from django.db.models import Sum
from rest_framework import serializers

from .models import SupplierLedger, SupplierPayment


class SupplierPaymentSerializer(serializers.ModelSerializer):
    """Serializer for individual payment entries."""

    payment_method_display = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )

    class Meta:
        model = SupplierPayment
        fields = [
            "id",
            "payment_no",
            "ledger",
            "amount",
            "payment_method",
            "payment_method_display",
            "payment_date",
            "reference",
            "notes",
            "is_cancelled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "payment_no", "created_at",
                            "updated_at", "payment_method_display"]

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError(
                "Payment amount must be greater than 0.")
        return value


class SupplierLedgerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ledger list view (no nested payments)."""

    supplier_name = serializers.CharField(
        source="supplier.name", read_only=True)
    supplier_code = serializers.CharField(
        source="supplier.supplier_code", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    payment_count = serializers.SerializerMethodField()

    class Meta:
        model = SupplierLedger
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "supplier_code",
            "branch",
            "branch_name",
            "purchase_order",
            "po_number",
            "po_date",
            "debit_amount",
            "credit_amount",
            "balance",
            "notes",
            "payment_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "credit_amount",
            "balance",
            "created_at",
            "updated_at",
        ]

    def get_payment_count(self, obj):
        return obj.payments.filter(is_cancelled=False).count()


class SupplierLedgerDetailSerializer(serializers.ModelSerializer):
    """Full serializer for ledger detail view — includes nested payments."""

    supplier_name = serializers.CharField(
        source="supplier.name", read_only=True)
    supplier_code = serializers.CharField(
        source="supplier.supplier_code", read_only=True)
    supplier_phone = serializers.CharField(
        source="supplier.phone", read_only=True)
    supplier_email = serializers.CharField(
        source="supplier.email", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    payments = SupplierPaymentSerializer(many=True, read_only=True)
    po_status = serializers.CharField(
        source="purchase_order.status", read_only=True, default=""
    )

    class Meta:
        model = SupplierLedger
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "supplier_code",
            "supplier_phone",
            "supplier_email",
            "branch",
            "branch_name",
            "purchase_order",
            "po_number",
            "po_date",
            "po_status",
            "debit_amount",
            "credit_amount",
            "balance",
            "notes",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "credit_amount",
            "balance",
            "created_at",
            "updated_at",
        ]


class SupplierLedgerSummarySerializer(serializers.Serializer):
    """Summary aggregation for a supplier or company."""

    supplier = serializers.UUIDField(required=False, allow_null=True)
    supplier_name = serializers.CharField(required=False, allow_null=True)
    total_debit = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_credit = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    ledger_count = serializers.IntegerField()
