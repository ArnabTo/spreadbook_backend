from decimal import Clamped

from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import User as GenUser

User = get_user_model()


class UserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True}}


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenUser
        fields = "__all__"
        # extra_kwargs = {'password': {'write_only': True}}
        extra_kwargs = {
            "password": {"write_only": True},
            # 'password': {'required': False},
        }


class UserCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = GenUser
        fields = [
            "id",
            "name",
            "email",
            "phoneNumber",
            "is_staff",
            "company",
            "fullAddress",
            "addressType",
            "primary",
            "first_name",
            "last_name",
            "role",
            "state",
            "zipCode",
            "avatarUrl",
            "address",
            "city",
            "status",
            "country",
            "about",
        ]

        # extra_kwargs = {'password': {'write_only': True}}
        extra_kwargs = {
            "password": {"write_only": True},
            # 'password': {'required': False},
        }


class UserCompanyBranchSerializer(serializers.ModelSerializer):
    """Enhanced serializer for company-branch users with permissions and shifts"""

    phone = serializers.CharField(source="phoneNumber", read_only=True)
    salary = serializers.SerializerMethodField()
    paymentType = serializers.SerializerMethodField()
    payrollStatus = serializers.SerializerMethodField()
    payrollId = serializers.SerializerMethodField()
    startDate = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    shifts = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._payroll_cache = {}

    class Meta:
        model = GenUser
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "role",
            "salary",
            "paymentType",
            "payrollStatus",
            "payrollId",
            "status",
            "startDate",
            "permissions",
            "shifts",
            # Additional fields for compatibility
            "phoneNumber",
            "company",
            "fullAddress",
            "city",
            "state",
            "country",
            "avatarUrl",
        ]

    def _get_payroll(self, obj):
        """Get payroll record using OneToOne relationship with caching"""
        if obj.id in self._payroll_cache:
            return self._payroll_cache[obj.id]

        try:
            # Use the OneToOne relationship from User.payroll
            payroll = getattr(obj, "payroll", None)
            self._payroll_cache[obj.id] = payroll
            return payroll
        except AttributeError:
            self._payroll_cache[obj.id] = None
            return None

    def get_salary(self, obj):
        """Get salary from SetEmployeePayroll model"""
        payroll = self._get_payroll(obj)

        if payroll and payroll.salary is not None:
            return float(payroll.salary)

        # Return null if no payroll record exists or salary is null
        return None

    def get_paymentType(self, obj):
        """Get payment type from SetEmployeePayroll model"""
        payroll = self._get_payroll(obj)

        if payroll and payroll.payment_type:
            return payroll.payment_type

        # Return null if no payroll record exists or payment_type is null
        return None

    def get_payrollStatus(self, obj):
        """Get payroll status from SetEmployeePayroll model"""
        payroll = self._get_payroll(obj)

        if payroll:
            return payroll.status if payroll.status else "inactive"

        return "not_set"  # No payroll record exists

    def get_payrollId(self, obj):
        """Get payroll ID from SetEmployeePayroll model"""
        payroll = self._get_payroll(obj)

        if payroll:
            return payroll.id

        return None  # No payroll record exists

    def get_startDate(self, obj):
        """Get start date - using created_at or date_joined"""
        if hasattr(obj, "date_joined") and obj.date_joined:
            return obj.date_joined.strftime("%Y-%m-%d")
        elif obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d")
        return None

    def get_permissions(self, obj):
        """Get user permissions based on role - matching your frontend Staff[] examples"""
        # Default permissions structure matching your frontend
        default_permissions = {
            "pos": False,
            "kitchen": False,
            "inventory": False,
            "reports": False,
            "settings": False,
        }

        # Permission mapping based on your frontend examples
        role_permissions = {
            "software_owner": {
                "pos": True,
                "kitchen": True,
                "inventory": True,
                "reports": True,
                "settings": True,
            },
            "super_admin": {
                "pos": True,
                "kitchen": True,
                "inventory": True,
                "reports": True,
                "settings": True,
            },
            "admin": {
                "pos": True,
                "kitchen": True,
                "inventory": True,
                "reports": True,
                "settings": True,
            },
            "manager": {  # John Martinez example - all permissions
                "pos": True,
                "kitchen": True,
                "inventory": True,
                "reports": True,
                "settings": True,
            },
            "chef": {  # Mike Rodriguez example - kitchen + inventory
                "pos": False,
                "kitchen": True,
                "inventory": True,
                "reports": False,
                "settings": False,
            },
            "waiter": {  # Sarah Chen example - pos only
                "pos": True,
                "kitchen": False,
                "inventory": False,
                "reports": False,
                "settings": False,
            },
            "bartender": {  # Emma Wilson example - pos + inventory
                "pos": True,
                "kitchen": False,
                "inventory": True,
                "reports": False,
                "settings": False,
            },
            "cashier": {
                "pos": True,
                "kitchen": False,
                "inventory": False,
                "reports": False,
                "settings": False,
            },
            "staff": {
                "pos": True,
                "kitchen": False,
                "inventory": False,
                "reports": False,
                "settings": False,
            },
        }

        return role_permissions.get(obj.role, default_permissions)

    def get_shifts(self, obj):
        """Get user shifts - placeholder for now, can be integrated with shift model"""
        # If you have a Shift model related to User, you can do:
        # return [{'id': s.id, 'name': s.name, 'start_time': s.start_time, ...} for s in obj.shifts.all()]

        # For now, returning empty array as in your example
        return []


class ResetPassUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenUser
        fields = [
            "id",
            "name",
            "email",
            "phoneNumber",
            "is_staff",
            "company",
            "fullAddress",
            "addressType",
            "primary",
            "first_name",
            "last_name",
            "role",
            "state",
            "zipCode",
            "avatarUrl",
            "address",
            "city",
            "status",
            "country",
            "about",
        ]

        # extra_kwargs = {'password': {'write_only': True}}
        extra_kwargs = {
            "password": {"write_only": True},
            # 'password': {'required': False},
        }


class ResetPassUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenUser
        fields = ["id", "name", "email", "phoneNumber", "password"]
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": False},
        }

    def update(self, instance, validated_data):
        print(validated_data["password"])
        instance.set_password(validated_data["password"])
        instance.save()
        return instance


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenUser
        fields = [
            "id",
            "name",
            "email",
            "phoneNumber",
            "is_staff",
            "brand_logo",
            "company",
            "fullAddress",
            "addressType",
            "primary",
            "first_name",
            "last_name",
            "role",
            "state",
            "zipCode",
            "avatarUrl",
            "address",
            "city",
            "status",
            "country",
            "about",
        ]

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenUser
        fields = [
            "id",
            "name",
            "email",
            "phoneNumber",
            "is_staff",
            "brand_logo",
            "company",
            "fullAddress",
            "addressType",
            "primary",
            "first_name",
            "last_name",
            "role",
            "state",
            "zipCode",
            "avatarUrl",
            "address",
            "city",
            "status",
            "country",
            "about",
            "password",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = GenUser(**validated_data)
        user.set_password(validated_data["password"])
        user.save()
        return user


class CreateCompanyUserSerializer(serializers.ModelSerializer):
    # Add salary fields for payroll integration
    salary = serializers.FloatField(required=False, allow_null=True)
    paymentType = serializers.ChoiceField(
        choices=[("hourly", "Hourly"), ("monthly", "Monthly")],
        required=False,
        allow_null=True,
    )

    class Meta:
        model = GenUser
        fields = [
            "id",
            "name",
            "email",
            "phoneNumber",
            "is_staff",
            "brand_logo",
            "company",
            "fullAddress",
            "addressType",
            "primary",
            "first_name",
            "last_name",
            "role",
            "state",
            "zipCode",
            "avatarUrl",
            "address",
            "city",
            "status",
            "country",
            "about",
            "password",
            # Add payroll fields
            "salary",
            "paymentType",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        # Extract salary data before creating user
        salary = validated_data.pop("salary", None)
        payment_type = validated_data.pop("paymentType", None)

        # Extract password to handle it separately
        password = validated_data.pop("password")

        # Create user
        user = GenUser(**validated_data)
        user.set_password(password)
        user.save()

        # Create payroll record if salary information is provided
        if salary is not None:
            from payroll.models import SetEmployeePayroll

            # Map frontend paymentType to backend payment_type choices
            backend_payment_type = "cash"  # Default
            if payment_type == "hourly":
                backend_payment_type = "cash"  # You can adjust this mapping
            elif payment_type == "monthly":
                backend_payment_type = "bank"  # You can adjust this mapping

            # Create payroll record and establish OneToOne relationship
            payroll = SetEmployeePayroll.objects.create(
                salary=salary,
                payment_type=backend_payment_type,
                status="active",
                company_id=user.companyId.id if user.companyId else None,
                company=user.company if user.company else None,
            )

            # Link the payroll to the user via the OneToOne relationship
            user.payroll = payroll
            user.save()

        return user


class RestaurantLoginSerializer(serializers.Serializer):
    """Serializer for restaurant login matching frontend expectations"""

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile data matching frontend User interface"""

    fullName = serializers.CharField(source="get_full_name", read_only=True)
    branchAccess = serializers.SerializerMethodField()
    avatarUrl = serializers.ImageField(read_only=True)
    companyId = serializers.SerializerMethodField()
    resellerId = serializers.SerializerMethodField()

    class Meta:
        model = GenUser
        fields = [
            "id",
            "username",
            "email",
            "fullName",
            "role",
            "companyId",
            "resellerId",
            "branchAccess",
            "avatarUrl",
            "status",
            "last_login",
            "created_at",
        ]

    def get_full_name(self, obj):
        return obj.fullName or obj.name or f"{obj.first_name} {obj.last_name}".strip()

    def get_companyId(self, obj):
        return obj.companyId.id if obj.companyId else None

    def get_resellerId(self, obj):
        return obj.resellerId.id if obj.resellerId else None

    def get_branchAccess(self, obj):
        return (
            list(obj.branchAccess.values_list("id", flat=True))
            if obj.branchAccess.exists()
            else []
        )


class UserManagementSerializer(serializers.ModelSerializer):
    """Enhanced serializer for user management with company/branch info"""

    company_name = serializers.CharField(source="company", read_only=True)
    managed_branches = serializers.SerializerMethodField()
    branch_names = serializers.SerializerMethodField()
    fullName = serializers.CharField(source="get_full_name", read_only=True)
    companyId = serializers.SerializerMethodField()
    resellerId = serializers.SerializerMethodField()
    branchAccess = serializers.SerializerMethodField()

    class Meta:
        model = GenUser
        fields = [
            "id",
            "username",
            "email",
            "fullName",
            "name",
            "first_name",
            "last_name",
            "role",
            "phoneNumber",
            "company",
            "company_name",
            "companyId",
            "resellerId",
            "branchAccess",
            "branch_names",
            "managed_branches",
            "avatarUrl",
            "fullAddress",
            "city",
            "state",
            "country",
            "status",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "last_login"]
        extra_kwargs = {"password": {"write_only": True}}

    def get_full_name(self, obj):
        return obj.fullName or obj.name or f"{obj.first_name} {obj.last_name}".strip()

    def get_companyId(self, obj):
        return obj.companyId.id if obj.companyId else None

    def get_resellerId(self, obj):
        return obj.resellerId.id if obj.resellerId else None

    def get_branchAccess(self, obj):
        return (
            list(obj.branchAccess.values_list("id", flat=True))
            if obj.branchAccess.exists()
            else []
        )

    def get_managed_branches(self, obj):
        """Get branches this user manages"""
        from company.models import Branch

        branches = Branch.objects.filter(manager=obj)
        return [{"id": b.id, "name": b.name, "code": b.code} for b in branches]

    def get_branch_names(self, obj):
        """Get names of branches user has access to"""
        if not obj.branchAccess.exists():
            return []

        from company.models import Branch

        branches = obj.branchAccess.all()
        return [b.name for b in branches]


class CreateRestaurantUserSerializer(serializers.ModelSerializer):
    """Serializer for creating restaurant users with proper validation"""

    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    # Handle foreign key fields properly - using SerializerMethodField for read operations
    companyId = serializers.IntegerField(
        required=False, allow_null=True, write_only=True
    )
    resellerId = serializers.IntegerField(
        required=False, allow_null=True, write_only=True
    )
    branchAccess = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )

    class Meta:
        model = GenUser
        fields = [
            "username",
            "email",
            "password",
            "confirm_password",
            "fullName",
            "name",
            "role",
            "phoneNumber",
            "company",
            "companyId",
            "resellerId",
            "branchAccess",
            "fullAddress",
            "city",
            "state",
            "country",
            "status",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "role": {"required": True},
        }

    def validate_companyId(self, value):
        """Validate company ID exists"""
        if value is not None:
            try:
                from company.models import Company

                Company.objects.get(id=value)
            except Company.DoesNotExist:
                raise serializers.ValidationError("Company does not exist")
        return value

    def validate_resellerId(self, value):
        """Validate reseller ID exists"""
        if value is not None:
            try:
                from reseller.models import Reseller

                Reseller.objects.get(id=value)
            except Reseller.DoesNotExist:
                raise serializers.ValidationError("Reseller does not exist")
        return value

    def validate_branchAccess(self, value):
        """Validate branch IDs exist"""
        if value:
            try:
                from company.models import Branch

                existing_ids = set(
                    Branch.objects.filter(id__in=value).values_list("id", flat=True)
                )
                invalid_ids = set(value) - existing_ids
                if invalid_ids:
                    raise serializers.ValidationError(
                        f"Invalid branch IDs: {list(invalid_ids)}"
                    )
            except Exception as e:
                raise serializers.ValidationError("Error validating branch access")
        return value

    def validate(self, data):
        """Validate password confirmation and role permissions"""
        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError("Passwords do not match")

        # Remove confirm_password from data
        data.pop("confirm_password", None)

        return data

    def create(self, validated_data):
        """Create user with encrypted password"""
        password = validated_data.pop("password")

        # Handle foreign key fields
        company_id = validated_data.pop("companyId", None)
        reseller_id = validated_data.pop("resellerId", None)
        branch_ids = validated_data.pop("branchAccess", [])

        user = GenUser(**validated_data)
        user.set_password(password)

        # Set username to email if not provided
        if not user.username:
            user.username = user.email

        # Set foreign key relationships
        if company_id:
            try:
                from company.models import Company

                user.companyId = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                pass

        if reseller_id:
            try:
                from reseller.models import Reseller

                user.resellerId = Reseller.objects.get(id=reseller_id)
            except Reseller.DoesNotExist:
                pass

        user.save()

        # Set many-to-many relationship
        if branch_ids:
            try:
                from company.models import Branch

                branches = Branch.objects.filter(id__in=branch_ids)
                user.branchAccess.set(branches)
            except Exception:
                pass

        return user


class BulkUserUpdateSerializer(serializers.Serializer):
    """Serializer for bulk user operations"""

    user_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    action = serializers.ChoiceField(
        choices=[
            ("activate", "Activate"),
            ("deactivate", "Deactivate"),
            ("delete", "Delete"),
            ("change_role", "Change Role"),
            ("update_branch_access", "Update Branch Access"),
        ]
    )

    # Optional fields for specific actions
    new_role = serializers.CharField(required=False)
    branch_access = serializers.ListField(child=serializers.CharField(), required=False)
