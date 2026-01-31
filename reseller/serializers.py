from rest_framework import serializers
from .models import Reseller, ResellerCommission


class ResellerSerializer(serializers.ModelSerializer):
    """Serializer for Reseller model"""

    commission_rate_display = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Reseller
        fields = [
            "id",
            "name",
            "companyName",
            "email",
            "phone",
            "address",
            "city",
            "country",
            "defaultCommission",
            "commission_rate_display",
            "status",
            "is_active",
            "totalClients",
            "totalRevenue",
            "commissionEarned",
            "joinedDate",
            "lastActive",
            "created_at",
            "updated_at",
            "isWhiteLabel",
            "whiteLabelCompanyName",
            "whiteLabelLogo",
            "whiteLabelPrimaryColor",
            "whiteLabelSecondaryColor",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "lastActive"]

    def validate_email(self, value):
        """Validate email uniqueness"""
        if self.instance and self.instance.email == value:
            return value

        if Reseller.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A reseller with this email already exists."
            )
        return value

    def validate_defaultCommission(self, value):
        """Validate commission rate"""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Commission rate must be between 0 and 100 percent."
            )
        return value


class ResellerListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing resellers"""

    commission_rate_display = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Reseller
        fields = [
            "id",
            "name",
            "companyName",
            "email",
            "phone",
            "city",
            "country",
            "commission_rate_display",
            "status",
            "is_active",
            "totalClients",
            "totalRevenue",
            "commissionEarned",
            "joinedDate",
            "isWhiteLabel",
            "whiteLabelCompanyName",
            "whiteLabelLogo",
            "whiteLabelPrimaryColor",
            "whiteLabelSecondaryColor",
        ]


class ResellerCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating resellers"""

    class Meta:
        model = Reseller
        fields = [
            "name",
            "companyName",
            "email",
            "phone",
            "address",
            "city",
            "country",
            "defaultCommission",
            "status",
            "isWhiteLabel",
            "whiteLabelCompanyName",
            "whiteLabelLogo",
            "whiteLabelPrimaryColor",
            "whiteLabelSecondaryColor",
        ]

    def validate_email(self, value):
        """Validate email uniqueness"""
        if self.instance and self.instance.email == value:
            return value

        if Reseller.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A reseller with this email already exists."
            )
        return value


class ResellerCommissionSerializer(serializers.ModelSerializer):
    """Serializer for ResellerCommission model"""

    reseller_name = serializers.CharField(source="reseller.name", read_only=True)
    company_name = serializers.CharField(source="client_company.name", read_only=True)

    class Meta:
        model = ResellerCommission
        fields = [
            "id",
            "reseller",
            "reseller_name",
            "client_company",
            "company_name",
            "revenue_amount",
            "commission_rate",
            "commission_amount",
            "is_paid",
            "paid_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "commission_amount", "created_at", "updated_at"]

    def validate(self, data):
        """Validate commission data"""
        if data.get("revenue_amount", 0) < 0:
            raise serializers.ValidationError("Revenue amount cannot be negative.")

        if data.get("commission_rate", 0) < 0 or data.get("commission_rate", 0) > 100:
            raise serializers.ValidationError(
                "Commission rate must be between 0 and 100 percent."
            )

        return data


class ResellerStatsSerializer(serializers.ModelSerializer):
    """Serializer for reseller statistics"""

    commission_rate_display = serializers.ReadOnlyField()
    total_unpaid_commissions = serializers.SerializerMethodField()
    total_paid_commissions = serializers.SerializerMethodField()
    recent_commissions = serializers.SerializerMethodField()

    class Meta:
        model = Reseller
        fields = [
            "id",
            "name",
            "companyName",
            "totalClients",
            "totalRevenue",
            "commissionEarned",
            "commission_rate_display",
            "total_unpaid_commissions",
            "total_paid_commissions",
            "recent_commissions",
            "status",
            "joinedDate",
            "lastActive",
        ]

    def get_total_unpaid_commissions(self, obj):
        """Get total unpaid commission amount"""
        unpaid = (
            obj.commissions.filter(is_paid=False).aggregate(
                total=models.Sum("commission_amount")
            )["total"]
            or 0
        )
        return float(unpaid)

    def get_total_paid_commissions(self, obj):
        """Get total paid commission amount"""
        paid = (
            obj.commissions.filter(is_paid=True).aggregate(
                total=models.Sum("commission_amount")
            )["total"]
            or 0
        )
        return float(paid)

    def get_recent_commissions(self, obj):
        """Get recent commission records"""
        recent = obj.commissions.order_by("-created_at")[:5]
        return ResellerCommissionSerializer(recent, many=True).data


# Import models at the end to avoid circular imports
from django.db import models
