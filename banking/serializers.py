from rest_framework import serializers

from .models import BankAccount


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = [
            "id", "name", "account_number", "bank_name",
            "branch_name", "iban", "swift_code", "is_active",
            "companyId",
        ]
        extra_kwargs = {
            "companyId": {"required": False, "allow_null": True},
        }
