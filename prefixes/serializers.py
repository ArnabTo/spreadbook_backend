from rest_framework import serializers
from .models import Prefix


class PrefixListSerializer(serializers.ModelSerializer):
    financial_year_name = serializers.CharField(source="financial_year.name", read_only=True)

    class Meta:
        model = Prefix
        fields = [
            "id",
            "type",
            "prefix",
            "separator",
            "current_index",
            "from_date",
            "to_date",
            "financial_year",
            "financial_year_name",
            "applicable",
            "exclude_tax",
            "narration",
            "prefix_series",
            "extra_config",
        ]


class PrefixDetailSerializer(serializers.ModelSerializer):
    financial_year_name = serializers.CharField(source="financial_year.name", read_only=True)

    class Meta:
        model = Prefix
        fields = [
            "id",
            "company",
            "type",
            "prefix",
            "separator",
            "start_index",
            "current_index",
            "from_date",
            "to_date",
            "financial_year",
            "financial_year_name",
            "narration",
            "prefix_series",
            "applicable",
            "exclude_tax",
            "extra_config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at"]

    def validate_prefix(self, value):
        value = value.strip() if value else ""
        if not value:
            raise serializers.ValidationError("Prefix is required.")
        return value

    def validate_type(self, value):
        value = value.strip() if value else ""
        if not value:
            raise serializers.ValidationError("Type is required.")
        return value

    def validate(self, data):
        if data.get("from_date") and data.get("to_date") and data["from_date"] >= data["to_date"]:
            raise serializers.ValidationError(
                {"to_date": "From Date must be earlier than To Date."}
            )

        start_index = data.get("start_index", 0)
        current_index = data.get("current_index", 0)
        if current_index < start_index:
            raise serializers.ValidationError(
                {"current_index": "Current Index must be >= Start Index."}
            )

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["company"] = request.user.companyId
        return super().create(validated_data)
