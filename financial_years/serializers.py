from rest_framework import serializers
from .models import FinancialYear


class FinancialYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialYear
        fields = [
            "id",
            "company",
            "name",
            "from_date",
            "to_date",
            "closed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip() if value else ""
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate(self, data):
        if data.get("from_date") and data.get("to_date") and data["from_date"] >= data["to_date"]:
            raise serializers.ValidationError(
                {"to_date": "From Date must be earlier than To Date."}
            )
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["company"] = request.user.companyId
        return super().create(validated_data)
