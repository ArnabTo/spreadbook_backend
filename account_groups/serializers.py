from rest_framework import serializers
from .models import AccountGroup, AccountGroupParent


class AccountGroupParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountGroupParent
        fields = ["id", "name", "is_active"]


class AccountGroupListSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = AccountGroup
        fields = [
            "id",
            "name",
            "account_code",
            "parent",
            "parent_name",
            "created_at",
            "updated_at",
        ]


class AccountGroupDetailSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = AccountGroup
        fields = [
            "id",
            "company",
            "name",
            "account_code",
            "parent",
            "parent_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip() if value else ""
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_account_code(self, value):
        value = value.strip() if value else ""
        if not value:
            raise serializers.ValidationError("Account code is required.")
        return value

    def validate_parent(self, value):
        if not AccountGroupParent.objects.filter(id=value.id, is_active=True).exists():
            raise serializers.ValidationError("Selected parent group does not exist or is inactive.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["company"] = request.user.companyId
        return super().create(validated_data)
