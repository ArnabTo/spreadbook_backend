from rest_framework import serializers
from .models import Customer, CustomerAttachment, ALLOWED_ATTACHMENT_EXTENSIONS
import os


class CustomerAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAttachment
        fields = ["id", "file", "original_filename", "file_size", "uploaded_at"]
        read_only_fields = ["id", "original_filename", "file_size", "uploaded_at"]

    def validate_file(self, value):
        ext = os.path.splitext(value.name)[1].lower().lstrip(".")
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}'. Allowed: {', '.join(ALLOWED_ATTACHMENT_EXTENSIONS)}"
            )
        return value

    def create(self, validated_data):
        validated_data["original_filename"] = validated_data["file"].name
        validated_data["file_size"] = validated_data["file"].size
        return super().create(validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="phoneNumber", required=False, allow_blank=True)
    attachments = CustomerAttachmentSerializer(many=True, read_only=True)
    country_name = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    sales_person_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "companyId",
            "branch",
            # Party Info
            "name",
            "display_name",
            "arabic_name",
            "address",
            "arabic_address",
            "customer_code",
            "phoneNumber",
            "mobile_number",
            "phone",
            "email",
            # Accounting
            "vat_no",
            "cr_number",
            "is_effected_to_ledger",
            "credit_period",
            "credit_limit",
            "opening_balance",
            # Contact & Sales
            "contact_person",
            "sales_person",
            "sales_person_name",
            # Classification
            "category",
            "status",
            # Business metrics (read-only)
            "totalOrders",
            "totalSpent",
            "loyaltyPoints",
            "lastVisit",
            # Bilingual Address
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
            # File attachments
            "attachments",
            # Legacy
            "fullAddress",
            "addressType",
            "gender",
            "company",
            "url",
            "balance",
            "previous_balance",
            "notes",
            "avatarUrl",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "companyId",
            "customer_code",
            "country_name",
            "state_name",
            "sales_person_name",
            "attachments",
            "totalOrders",
            "totalSpent",
            "loyaltyPoints",
            "lastVisit",
            "created_at",
            "updated_at",
        )

    def get_country_name(self, obj):
        return obj.country_ref.name if obj.country_ref else None

    def get_state_name(self, obj):
        return obj.state_ref.name if obj.state_ref else None

    def get_sales_person_name(self, obj):
        if obj.sales_person:
            return obj.sales_person.get_full_name() or obj.sales_person.username
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.phoneNumber:
            data["phone"] = str(instance.phoneNumber)
        if instance.fullAddress:
            data["fullAddress"] = str(instance.fullAddress)
        if instance.totalSpent is not None:
            data["totalSpent"] = float(instance.totalSpent)
        if instance.balance is not None:
            data["balance"] = float(instance.balance)
        if instance.lastVisit:
            data["lastVisit"] = instance.lastVisit.strftime("%Y-%m-%d")
        return data

    def create(self, validated_data):
        if "phone" in validated_data and validated_data.get("phone") is not None:
            validated_data["phoneNumber"] = validated_data.pop("phone")
        else:
            validated_data.pop("phone", None)

        validated_data.setdefault("totalOrders", 0)
        validated_data.setdefault("totalSpent", 0)
        validated_data.setdefault("loyaltyPoints", 0)
        return Customer.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if "phone" in validated_data:
            validated_data["phoneNumber"] = validated_data.pop("phone")
        validated_data.pop("totalOrders", None)
        validated_data.pop("totalSpent", None)
        validated_data.pop("loyaltyPoints", None)
        return super().update(instance, validated_data)

    def validate_is_effected_to_ledger(self, value):
        if value is not True:
            raise serializers.ValidationError("Is Effected To Ledger must always be true.")
        return True

    def validate_credit_period(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Credit Period must be >= 0.")
        return value

    def validate_credit_limit(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Credit Limit must be >= 0.")
        return value

    def validate_email(self, value):
        if value:
            qs = Customer.objects.filter(email=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A customer with this email already exists.")
        return value

    def validate(self, data):
        name = data.get("name")
        email = data.get("email")
        if not name and not email:
            raise serializers.ValidationError("Customer must have either name or email address.")
        return data
