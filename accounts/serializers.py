from rest_framework import serializers

from accounts.models.account_models import Account
from accounts.models.bank_account_model import Bank


class AccountSerializer(serializers.ModelSerializer):
    parent_name = serializers.SerializerMethodField()
    country_name = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id",
            "company",
            "parent",
            "parent_name",
            "display_name",
            "name",
            "mailing_name",
            "arabic_name",
            "phone_number",
            "mobile_number",
            "bank_name",
            "arabic_bank_name",
            "bank_account_number",
            "iban_no",
            "branch_name",
            "branch_code",
            "swift_code",
            "email",
            "description",
            "opening_balance",
            "is_debit",
            "cheque_print_enabled",
            "country_ref",
            "country_name",
            "arabic_country",
            "state_ref",
            "state_name",
            "arabic_state",
            "city",
            "arabic_city",
            "building_no",
            "arabic_building_no",
            "street_name",
            "arabic_street_name",
            "district",
            "arabic_district",
            "additional_no",
            "arabic_additional_no",
            "zip_code",
            "arabic_zip_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "company",
            "parent_name",
            "country_name",
            "state_name",
            "created_at",
            "updated_at",
        )

    def get_parent_name(self, obj):
        return obj.parent.name if obj.parent and hasattr(obj.parent, 'name') else None

    def get_country_name(self, obj):
        return obj.country_ref.name if obj.country_ref else None

    def get_state_name(self, obj):
        return obj.state_ref.name if obj.state_ref else None

    def validate_cheque_print_enabled(self, value):
        if value is not False:
            raise serializers.ValidationError("Cheque Print Enabled must always be false.")
        return False

    def validate(self, data):
        if not data.get("name"):
            raise serializers.ValidationError({"name": "Name is required."})
        if not data.get("parent") and not self.instance:
            raise serializers.ValidationError({"parent": "Parent is required."})
        if not data.get("parent") and self.instance and not self.instance.parent:
            raise serializers.ValidationError({"parent": "Parent is required."})
        return data


# ── Legacy Bank serializer (preserved) ──

class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = "__all__"

    def create(self, validated_data):
        bank = Bank.objects.create(
            company_id=self.context["request"].user.company_id,
            creator=self.context["request"].user,
            company=self.context["request"].user.company,
            **validated_data
        )
        return bank

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

