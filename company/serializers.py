from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from .models import Company, Branch, CompanyCustomization, Warehouse

User = get_user_model()


class CompanyCustomizationSerializer(serializers.ModelSerializer):
    """Serializer for CompanyCustomization model"""

    class Meta:
        model = CompanyCustomization
        fields = [
            "id",
            "company",
            "primaryColor",
            "currency",
            "taxRate",
            "timezone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WarehouseSerializer(serializers.ModelSerializer):
    """Serializer for Warehouse model matching frontend structure"""

    companyId = serializers.ReadOnlyField()
    branch_count = serializers.ReadOnlyField()
    manager = serializers.CharField(
        source="manager_name", required=False, allow_blank=True, allow_null=True
    )
    phone = serializers.CharField(
        source="phoneNumber", required=False, allow_blank=True, allow_null=True
    )
    location = serializers.CharField(
        source="fullAddress", required=False, allow_blank=True, allow_null=True
    )
    parentWarehouseId = serializers.PrimaryKeyRelatedField(
        source="parent_warehouse",
        queryset=Warehouse.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "companyId",
            "company",
            "parentWarehouseId",
            "name",
            "code",
            "location",
            "phone",
            "phoneNumber",
            "email",
            "fullAddress",
            "city",
            "state",
            "country",
            "postal_code",
            "manager",
            "manager_name",
            "capacity",
            "warehouseType",
            "status",
            "is_active",
            "branch_count",
            "postedAt",
            "updateAt",
        ]
        read_only_fields = ["id", "code", "companyId",
                            "branch_count", "postedAt", "updateAt"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["id"] = str(representation["id"])
        if not representation.get("location") and representation.get("fullAddress"):
            representation["location"] = representation["fullAddress"]
        if not representation.get("manager") and representation.get("manager_name"):
            representation["manager"] = representation["manager_name"]
        if not representation.get("manager"):
            representation["manager"] = "No manager assigned"
        return representation


class BranchSerializer(serializers.ModelSerializer):
    """Serializer for restaurant branches matching frontend structure"""

    # Frontend compatibility fields
    companyId = serializers.ReadOnlyField()
    manager = serializers.CharField(
        source="manager_name", required=False, allow_blank=True
    )
    phone = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    openingHours = serializers.CharField(required=False, allow_blank=True)
    todaySales = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    monthSales = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    activeOrders = serializers.IntegerField(default=0)
    activeTables = serializers.IntegerField(default=0)
    staff = serializers.IntegerField(default=0)
    status = serializers.ChoiceField(
        choices=[("active", "Active"), ("inactive", "Inactive")], default="active"
    )
    warehouseId = serializers.PrimaryKeyRelatedField(
        source="warehouse",
        queryset=Warehouse.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Branch
        fields = [
            # Frontend required fields
            "id",
            "companyId",
            "name",
            "location",
            "manager",
            "phone",
            "status",
            "openingHours",
            "todaySales",
            "monthSales",
            "activeOrders",
            "activeTables",
            "staff",
            # Warehouse link
            "warehouseId",
            # Additional backend fields
            "code",
            "company",
            "phoneNumber",
            "email",
            "fullAddress",
            "city",
            "state",
            "country",
            "postal_code",
            "manager_name",
            "opening_hours",
            "seating_capacity",
            "delivery_radius",
            "is_active",
            "postedAt",
            "updateAt",
        ]
        read_only_fields = ["id", "postedAt", "updateAt", "code", "companyId"]

    def create(self, validated_data):
        # Handle manager field (it's coming as manager_name)
        manager_name = validated_data.pop("manager_name", None)
        if manager_name:
            validated_data["manager_name"] = manager_name
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Handle manager field (it's coming as manager_name)
        manager_name = validated_data.pop("manager_name", None)
        if manager_name:
            validated_data["manager_name"] = manager_name
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Customize the output format to match frontend expectations"""
        representation = super().to_representation(instance)

        # Ensure numeric fields are properly formatted
        representation["todaySales"] = float(
            representation.get("todaySales", 0))
        representation["monthSales"] = float(
            representation.get("monthSales", 0))

        # Ensure string ID for frontend compatibility
        representation["id"] = str(representation["id"])

        # Map fullAddress to location if location is empty
        if not representation.get("location") and representation.get("fullAddress"):
            representation["location"] = representation["fullAddress"]

        # Ensure location has a fallback value
        if not representation.get("location"):
            city = representation.get("city", "")
            country = representation.get("country", "")
            if city and country:
                representation["location"] = f"{city}, {country}"
            elif city:
                representation["location"] = city
            elif country:
                representation["location"] = country
            else:
                representation["location"] = "Location not set"

        # Map manager_name to manager if manager is empty
        if not representation.get("manager") and representation.get("manager_name"):
            representation["manager"] = representation["manager_name"]

        # Ensure manager has a fallback value
        if not representation.get("manager"):
            representation["manager"] = "No manager assigned"

        # Map phoneNumber to phone if phone is empty
        if not representation.get("phone") and representation.get("phoneNumber"):
            representation["phone"] = representation["phoneNumber"]

        # Map opening_hours to openingHours if openingHours is empty
        if not representation.get("openingHours") and representation.get(
            "opening_hours"
        ):
            # Convert dict to readable string if needed
            opening_hours = representation.get("opening_hours")
            if isinstance(opening_hours, dict) and opening_hours:
                # Format opening hours from dict
                hours_list = []
                for day, hours in opening_hours.items():
                    if hours:
                        hours_list.append(f"{day.capitalize()}: {hours}")
                if hours_list:
                    representation["openingHours"] = ", ".join(
                        hours_list[:2]
                    )  # Show first 2 days
                else:
                    representation["openingHours"] = "Hours not set"
            else:
                representation["openingHours"] = "Hours not set"

        # Ensure openingHours has a fallback
        if not representation.get("openingHours"):
            representation["openingHours"] = "Hours not set"

        return representation


class CompanySerializer(serializers.ModelSerializer):
    """Enhanced serializer for Company model with features and customization"""

    branch_count = serializers.ReadOnlyField()
    branches_list = BranchSerializer(
        source="company_branches", many=True, read_only=True
    )
    branches = serializers.ReadOnlyField()  # This will use the @property method
    customization_details = CompanyCustomizationSerializer(
        source="customization", read_only=True
    )
    features = serializers.ReadOnlyField()

    # Flattened customization fields for frontend compatibility
    customization = serializers.SerializerMethodField()

    def get_customization(self, obj):
        """Return customization as a flattened object matching frontend interface"""
        if hasattr(obj, "customization") and obj.customization:
            return {
                "primaryColor": obj.customization.primaryColor or "#007bff",
                "currency": obj.customization.currency or "USD",
                "taxRate": float(obj.customization.taxRate or 0.0),
                "timezone": obj.customization.timezone or "UTC",
            }
        return {
            "primaryColor": "#007bff",
            "currency": "USD",
            "taxRate": 0.0,
            "timezone": "UTC",
        }

    class Meta:
        model = Company
        fields = [
            # Basic company info
            "id",
            "name",
            "email",
            "phoneNumber",
            "phone",
            "fullAddress",
            "address",
            "city",
            "country",
            "description",
            "avatarUrl",
            "logo",
            "url",
            "ownerName",
            "industry",
            "postedAt",
            "updateAt",
            "createdAt",
            "lastActive",
            # Business metrics
            "branches",
            "activeUsers",
            "monthlyRevenue",
            "branch_count",
            # Subscription fields
            "subscriptionPlan",
            "subscriptionStatus",
            "subscriptionPrice",
            "lastPaymentDate",
            "nextBillingDate",
            "paymentMethod",
            "daysOverdue",
            "trialEndsAt",
            "paymentType",
            # Reseller fields
            "resellerId",
            "resellerCommission",
            # Approval fields
            "approvalStatus",
            "approvalDate",
            "approvedBy",
            "rejectionReason",
            # Initial payment fields
            "initialPaymentAmount",
            "initialPaymentStatus",
            "initialPaymentDate",
            "initialPaymentMethod",
            "initialPaymentTransactionId",
            # Setup fee fields
            "setupFee",
            "setupFeeStatus",
            # Related data
            "branches_list",
            "customization_details",
            "customization",
            "features",
            # Receipt header fields
            "company_title_line1",
            "company_title_line2",
            "company_website",
        ]
        read_only_fields = [
            "id",
            "postedAt",
            "updateAt",
            "createdAt",
            "branch_count",
            "branches",
            "features",
            "branches_list",
        ]

    def create(self, validated_data):
        # Handle customization data if provided in request
        customization_data = (
            self.context.get("request", {}).data.get("customization", {})
            if self.context.get("request")
            else {}
        )

        # SaaS defaults: first 30 days trial (configurable)
        if not validated_data.get("subscriptionStatus"):
            trial_days = 30
            try:
                import os

                raw = os.getenv("DJANGO_TRIAL_DAYS")
                if raw:
                    trial_days = int(str(raw).strip())
            except Exception:
                trial_days = 30

            validated_data["subscriptionStatus"] = "trial"
            validated_data.setdefault("paymentType", "monthly")
            trial_ends = timezone.now() + timezone.timedelta(days=trial_days)
            validated_data.setdefault("trialEndsAt", trial_ends)
            validated_data.setdefault("nextBillingDate", trial_ends)
            validated_data.setdefault("daysOverdue", 0)

        # Create company
        company = super().create(validated_data)

        # Create or update customization if data provided
        if customization_data:
            CompanyCustomization.objects.update_or_create(
                company=company,
                defaults={
                    "primaryColor": customization_data.get("primaryColor"),
                    "currency": customization_data.get("currency"),
                    "taxRate": customization_data.get("taxRate"),
                    "timezone": customization_data.get("timezone"),
                },
            )

        return company

    def update(self, instance, validated_data):
        # Handle customization data if provided in request
        customization_data = (
            self.context.get("request", {}).data.get("customization", {})
            if self.context.get("request")
            else {}
        )

        # Update company
        company = super().update(instance, validated_data)

        # Update customization if data provided
        if customization_data:
            CompanyCustomization.objects.update_or_create(
                company=company,
                defaults={
                    "primaryColor": customization_data.get("primaryColor"),
                    "currency": customization_data.get("currency"),
                    "taxRate": customization_data.get("taxRate"),
                    "timezone": customization_data.get("timezone"),
                },
            )

        return company


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for company lists"""

    branch_count = serializers.ReadOnlyField()
    features = serializers.ReadOnlyField()
    customization = serializers.SerializerMethodField()

    def get_customization(self, obj):
        """Return customization as a flattened object matching frontend interface"""
        if hasattr(obj, "customization") and obj.customization:
            return {
                "primaryColor": obj.customization.primaryColor or "#007bff",
                "currency": obj.customization.currency or "USD",
                "taxRate": float(obj.customization.taxRate or 0.0),
                "timezone": obj.customization.timezone or "UTC",
            }
        return {
            "primaryColor": "#007bff",
            "currency": "USD",
            "taxRate": 0.0,
            "timezone": "UTC",
        }

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "email",
            "phoneNumber",
            "phone",
            "fullAddress",
            "address",
            "city",
            "country",
            "description",
            "avatarUrl",
            "logo",
            "url",
            "ownerName",
            "industry",
            "subscriptionPlan",
            "subscriptionStatus",
            "subscriptionPrice",
            "approvalStatus",
            "postedAt",
            "updateAt",
            "createdAt",
            "lastActive",
            "branch_count",
            "features",
            "customization",
        ]
        read_only_fields = [
            "id",
            "postedAt",
            "updateAt",
            "createdAt",
            "branch_count",
            "features",
            "customization",
        ]
