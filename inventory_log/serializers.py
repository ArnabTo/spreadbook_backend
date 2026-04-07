from rest_framework import serializers
from .models import InventoryLog


class InventoryLogSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    log_type_display = serializers.CharField(
        source="get_log_type_display", read_only=True
    )
    branch_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryLog
        fields = [
            "id",
            "category",
            "category_display",
            "log_type",
            "log_type_display",
            "quantity",
            "amount",
            "reference",
            "description",
            "companyId",
            "branch",
            "branch_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_branch_name(self, obj):
        if obj.branch:
            return getattr(obj.branch, "name", str(obj.branch))
        return None
