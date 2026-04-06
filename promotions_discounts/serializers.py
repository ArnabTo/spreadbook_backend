from rest_framework import serializers
from django.utils import timezone
from .models import Promotion, PromotionUsage


class PromotionSerializer(serializers.ModelSerializer):
    usage_percentage = serializers.ReadOnlyField()
    is_expiring_soon = serializers.ReadOnlyField()
    is_valid = serializers.ReadOnlyField()

    class Meta:
        model = Promotion
        fields = [
            "id",
            "name",
            "type",
            "value",
            "code",
            "start_date",
            "end_date",
            "min_order_value",
            "max_discount",
            "usage_limit",
            "used_count",
            "applicable_on",
            "target_items",
            "status",
            "description",
            "usage_percentage",
            "is_expiring_soon",
            "is_valid",
            "company",
            "branch",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "used_count",
            "created_at",
            "updated_at",
            "usage_percentage",
            "company",
        ]
        extra_kwargs = {
            "branch": {"required": False},
        }

    def validate(self, data):
        """Custom validation for promotion data"""
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("End date must be after start date")

        promotion_type = data.get("type")
        value = data.get("value")

        if promotion_type == "percentage" and value > 100:
            raise serializers.ValidationError("Percentage discount cannot exceed 100%")

        if value < 0:
            raise serializers.ValidationError("Discount value cannot be negative")

        return data

    def create(self, validated_data):
        """Set company and created_by from request context"""
        request = self.context.get("request")
        if request and request.user:
            validated_data["created_by"] = request.user
            company = getattr(request.user, "companyId", None) or getattr(
                request.user, "company", None
            )
            if company:
                validated_data["company"] = company

        return super().create(validated_data)


class PromotionUsageSerializer(serializers.ModelSerializer):
    promotion_name = serializers.CharField(source="promotion.name", read_only=True)
    promotion_code = serializers.CharField(source="promotion.code", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = PromotionUsage
        fields = [
            "id",
            "promotion",
            "promotion_name",
            "promotion_code",
            "order",
            "customer",
            "customer_name",
            "discount_amount",
            "order_value",
            "used_at",
        ]
        read_only_fields = [
            "id",
            "used_at",
            "promotion_name",
            "promotion_code",
            "customer_name",
        ]


class PromotionValidationSerializer(serializers.Serializer):
    """Serializer for validating promotion codes"""

    code = serializers.CharField(max_length=50)
    order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    customer_id = serializers.UUIDField(required=False)
    items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Optional cart line items: [{id, category, price, quantity}]",
    )

    def validate_code(self, value):
        """Validate that promotion code exists and is valid"""
        try:
            promotion = Promotion.objects.get(code=value.upper())
            if not promotion.is_valid():
                raise serializers.ValidationError(
                    "Promotion code is not valid or has expired"
                )
            return value.upper()
        except Promotion.DoesNotExist:
            raise serializers.ValidationError("Invalid promotion code")


class PromotionStatsSerializer(serializers.Serializer):
    """Serializer for promotion statistics"""

    total_promotions = serializers.IntegerField()
    active_promotions = serializers.IntegerField()
    scheduled_promotions = serializers.IntegerField()
    expired_promotions = serializers.IntegerField()
    total_redemptions = serializers.IntegerField()
    total_discount_given = serializers.DecimalField(max_digits=15, decimal_places=2)
    top_promotions = PromotionSerializer(many=True)


class BulkPromotionStatusSerializer(serializers.Serializer):
    """Serializer for bulk status updates"""

    promotion_ids = serializers.ListField(child=serializers.UUIDField())
    status = serializers.ChoiceField(choices=Promotion.STATUS_CHOICES)

    def validate_promotion_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one promotion ID is required")
        return value
