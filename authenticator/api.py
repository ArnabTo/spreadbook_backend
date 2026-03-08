import os

from rest_framework.decorators import permission_classes, api_view, action
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

# Import JWT functionality with error handling
try:
    from rest_framework_simplejwt.tokens import RefreshToken

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

from .models import User as GenUser
from .serializers import (
    UserSerializer,
    ResetPassUserSerializer,
    UpdateUserSerializer,
    CreateUserSerializer,
    UserManagementSerializer,
    CreateRestaurantUserSerializer,
    BulkUserUpdateSerializer,
    UserProfileSerializer,
    UserCompanySerializer,
    UserCompanyBranchSerializer,
    CreateCompanyUserSerializer,
)
from rest_framework import serializers, viewsets, permissions
from rest_framework import generics
from django.shortcuts import render

from common.drf_scoping import is_unrestricted_user
from common.permissions import IsBranchManagerOrAbove


class UserViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsBranchManagerOrAbove]

    # http_method_names= ['get']
    def get_queryset(self):
        user = self.request.user
        qs = GenUser.objects.all()

        if is_unrestricted_user(user) or bool(getattr(user, "is_superuser", False)):
            return qs

        company_id = getattr(user, "companyId_id", None)
        if company_id:
            return (
                qs.filter(companyId_id=company_id)
                .select_related("companyId", "resellerId")
                .prefetch_related("branchAccess")
            )

        # Fallback: derive company scope from branch access.
        if hasattr(user, "branchAccess") and user.branchAccess.exists():
            company_ids = set(user.branchAccess.values_list(
                "company_id", flat=True))
            return (
                qs.filter(companyId_id__in=list(company_ids))
                .select_related("companyId", "resellerId")
                .prefetch_related("branchAccess")
            )

        return GenUser.objects.none()


class UserCompanyViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = UserCompanySerializer
    permission_classes = [permissions.IsAuthenticated, IsBranchManagerOrAbove]

    # http_method_names= ['get']
    def get_queryset(self):
        return GenUser.objects.filter(companyId=self.request.user.companyId)


class UserCompanyBranchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for filtering users by both company and branch access
    Shows users from the same company who have access to the same branches
    Enhanced with permissions and shifts support
    """

    serializer_class = UserCompanyBranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsBranchManagerOrAbove]

    def get_queryset(self):
        """Filter users by company and branch access"""
        user = self.request.user

        # Start with users from the same company
        if not user.companyId:
            return GenUser.objects.none()

        # Base queryset: users from the same company
        queryset = GenUser.objects.filter(companyId=user.companyId)

        # If user has branch access, further filter by branch overlap
        if user.branchAccess.exists():
            # Get user's branch IDs
            user_branch_ids = list(
                user.branchAccess.values_list("id", flat=True))

            # Filter users who have access to at least one of the same branches
            # This uses the ManyToMany relationship to find overlapping branch access
            queryset = queryset.filter(
                branchAccess__id__in=user_branch_ids).distinct()

        return queryset.select_related("companyId").prefetch_related("branchAccess")

    def list(self, request, *args, **kwargs):
        """Override list to provide additional context"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Add context about filtering
        user = request.user
        user_branch_ids = (
            list(user.branchAccess.values_list("id", flat=True))
            if user.branchAccess.exists()
            else []
        )

        return Response(
            {
                "users": serializer.data,
                "filter_context": {
                    "company_id": user.companyId.id if user.companyId else None,
                    "user_branch_ids": user_branch_ids,
                    "total_users": queryset.count(),
                    "company_name": user.companyId.name if user.companyId else None,
                },
            }
        )

    @action(detail=False, methods=["get"])
    def by_branch(self, request):
        """Filter users by specific branch ID"""
        branch_id = request.query_params.get("branch_id")

        if not branch_id:
            return Response(
                {"error": "branch_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not user.companyId:
            return Response(
                {"error": "User must be associated with a company"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get users from same company with access to specific branch
        queryset = (
            GenUser.objects.filter(
                companyId=user.companyId, branchAccess__id=branch_id)
            .distinct()
            .select_related("companyId")
            .prefetch_related("branchAccess")
        )

        serializer = self.get_serializer(queryset, many=True)

        # Get branch name for context
        try:
            from company.models import Branch

            branch = Branch.objects.get(id=branch_id)
            branch_name = branch.name
        except Branch.DoesNotExist:
            branch_name = f"Branch ID {branch_id}"

        return Response(
            {
                "users": serializer.data,
                "filter_context": {
                    "company_id": user.companyId.id,
                    "company_name": user.companyId.name,
                    "branch_id": int(branch_id),
                    "branch_name": branch_name,
                    "total_users": queryset.count(),
                },
            }
        )

    @action(detail=False, methods=["get"])
    def branch_managers(self, request):
        """Get users who are managers with branch access in the same company"""
        user = request.user

        if not user.companyId:
            return Response(
                {"error": "User must be associated with a company"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get managers from same company
        queryset = (
            GenUser.objects.filter(companyId=user.companyId, role="manager")
            .exclude(branchAccess__isnull=True)
            .distinct()
            .select_related("companyId")
            .prefetch_related("branchAccess")
        )

        serializer = self.get_serializer(queryset, many=True)

        return Response(
            {
                "managers": serializer.data,
                "filter_context": {
                    "company_id": user.companyId.id,
                    "company_name": user.companyId.name,
                    "total_managers": queryset.count(),
                },
            }
        )

    @action(detail=False, methods=["get"])
    def test_connection(self, request):
        """Simple test endpoint to verify API is working"""
        user = request.user
        return Response(
            {
                "success": True,
                "message": "UserCompanyBranchViewSet is working",
                "user_id": user.id,
                "user_role": user.role,
                "has_company": bool(user.companyId),
                "has_branch_access": (
                    user.branchAccess.exists()
                    if hasattr(user, "branchAccess")
                    else False
                ),
            }
        )

    @action(detail=True, methods=["post"])
    def update_permissions(self, request, pk=None):
        """Update user permissions"""
        user = self.get_object()
        permissions_data = request.data.get("permissions", {})

        # Validate permissions structure
        valid_permissions = ["pos", "kitchen",
                             "inventory", "reports", "settings"]
        filtered_permissions = {
            key: bool(value)
            for key, value in permissions_data.items()
            if key in valid_permissions
        }

        if not filtered_permissions:
            return Response(
                {"error": "No valid permissions provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Here you can save permissions to a custom field or related model
        # For now, we'll return success with updated data

        serializer = self.get_serializer(user)
        return Response(
            {
                "success": True,
                "message": "Permissions updated successfully",
                "user": serializer.data,
            }
        )

    @action(detail=True, methods=["post"])
    def update_salary(self, request, pk=None):
        """Update user salary and payment type"""
        user = self.get_object()
        salary = request.data.get("salary")
        payment_type = request.data.get("paymentType")

        if salary is not None:
            # Here you can save salary to user model if you have the field
            # user.salary = salary
            pass

        if payment_type:
            # Here you can save payment type to user model if you have the field
            # user.payment_type = payment_type
            pass

        # user.save()

        serializer = self.get_serializer(user)
        return Response(
            {
                "success": True,
                "message": "Salary information updated successfully",
                "user": serializer.data,
            }
        )

    @action(detail=False, methods=["get"])
    def by_role(self, request):
        """Filter users by role within company and branch access"""
        role = request.query_params.get("role")

        if not role:
            return Response(
                {"error": "role parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(role=role)
        serializer = self.get_serializer(queryset, many=True)

        return Response(
            {
                "users": serializer.data,
                "filter_context": {
                    "role": role,
                    "total_users": queryset.count(),
                    "company_id": (
                        request.user.companyId.id if request.user.companyId else None
                    ),
                },
            }
        )

    @action(detail=False, methods=["get"])
    def staff_with_permissions(self, request):
        """Get staff with specific permission access"""
        permission = request.query_params.get(
            "permission"
        )  # pos, kitchen, inventory, reports, settings

        if not permission:
            return Response(
                {"error": "permission parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Define which roles have which permissions by default
        permission_roles = {
            "pos": [
                "waiter",
                "cashier",
                "staff",
                "manager",
                "admin",
                "super_admin",
                "software_owner",
            ],
            "kitchen": ["chef", "manager", "super_admin", "software_owner"],
            "inventory": ["manager", "admin", "super_admin", "software_owner"],
            "reports": ["manager", "admin", "super_admin", "software_owner"],
            "settings": ["super_admin", "software_owner"],
        }

        roles_with_permission = permission_roles.get(permission, [])
        queryset = self.get_queryset().filter(role__in=roles_with_permission)
        serializer = self.get_serializer(queryset, many=True)

        return Response(
            {
                "users": serializer.data,
                "filter_context": {
                    "permission": permission,
                    "roles_included": roles_with_permission,
                    "total_users": queryset.count(),
                },
            }
        )


class ResetPassUserViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = ResetPassUserSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return GenUser.objects.all()


class UpdateUserViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = UpdateUserSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return GenUser.objects.all()


class CreateUserViewSet(viewsets.ModelViewSet):
    # queryset = Product.objects.all()
    serializer_class = CreateUserSerializer

    # http_method_names= ['get']
    def get_queryset(self):
        return GenUser.objects.all()


class CreateCompanyUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for creating company users with payroll integration
    Handles staff member creation from Staff Management frontend
    """

    serializer_class = CreateCompanyUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GenUser.objects.all()

    def create(self, request, *args, **kwargs):
        """Create new staff member with payroll record"""
        data = request.data.copy()

        # Set company information from authenticated user
        if request.user.companyId:
            data["company"] = request.user.companyId.name
            # Don't set companyId in data as it's not in the serializer fields

        # Set default username to email if not provided
        if not data.get("username") and data.get("email"):
            data["username"] = data["email"]

        # Set default status if not provided
        if not data.get("status"):
            data["status"] = "active"

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            user = serializer.save()

            # Set company relationship
            if request.user.companyId:
                user.companyId = request.user.companyId
                user.save()

            # Add branch access - use branch_ids from request if explicitly provided,
            # otherwise fall back to the creating user's branch access
            branch_ids = request.data.get("branch_ids", None)
            if branch_ids is not None:
                # branch_ids was explicitly provided (even if empty list)
                if branch_ids:
                    from company.models import Branch
                    branches_qs = Branch.objects.filter(id__in=branch_ids)
                    user.branchAccess.set(branches_qs)
            elif (
                hasattr(request.user, "branchAccess")
                and request.user.branchAccess.exists()
            ):
                user.branchAccess.set(request.user.branchAccess.all())

            # Return success response with created user data
            response_serializer = UserCompanyBranchSerializer(user)
            return Response(
                {
                    "success": True,
                    "message": "Staff member created successfully",
                    "user": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def megashop_login(request):
    """
    MegaShop login endpoint that matches frontend expectations
    Accepts: username/email, password
    Returns: user data with JWT tokens
    """
    try:
        identifier = request.data.get("username") or request.data.get("email")
        password = request.data.get("password")

        if isinstance(identifier, str):
            identifier = identifier.strip()

        if not identifier or not password:
            return Response(
                {"error": "Username/email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find user by username OR email OR phone (case-insensitive)
        user = (
            GenUser.objects.filter(
                Q(username__iexact=identifier)
                | Q(email__iexact=identifier)
                | Q(phoneNumber__iexact=identifier)
            )
            .order_by("id")
            .first()
        )

        if not user:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )

        # Block explicitly banned users (keep other legacy statuses compatible)
        if getattr(user, "status", None) == "banned":
            return Response(
                {"error": "Account is banned"}, status=status.HTTP_403_FORBIDDEN
            )

        # Check password - Support both demo passwords and regular authentication
        is_valid_password = False

        allow_demo_passwords = bool(getattr(settings, "DEBUG", False)) or (
            (os.getenv("DJANGO_ALLOW_DEMO_PASSWORDS") or "").strip().lower()
            in {"1", "true", "t", "yes", "y", "on"}
        )

        # Demo password logic (intended for dev/demo only)
        if allow_demo_passwords:
            if user.role == "software_owner" and password == "owner123":
                is_valid_password = True
            elif user.role == "reseller" and password == "reseller123":
                is_valid_password = True
            elif user.role in ["super_admin", "admin"] and password == "admin123":
                is_valid_password = True
            elif user.role == "manager" and password == "manager123":
                is_valid_password = True
            elif (
                user.role in ["staff", "waiter", "chef", "cashier"]
                and password == "staff123"
            ):
                is_valid_password = True
            elif password == "demo123":
                # Fallback for backward compatibility
                is_valid_password = True

        if not is_valid_password:
            # Check against actual stored password
            is_valid_password = user.check_password(password)

        if not is_valid_password:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )

        # Update last login
        user.login_datetime = timezone.now()
        user.save()

        # Generate JWT tokens if available
        if JWT_AVAILABLE:
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            token_data = {
                "access_token": str(access_token),
                "refresh_token": str(refresh),
                "expires_in": access_token.lifetime.total_seconds(),
            }
        else:
            # Fallback to token authentication if JWT not available
            from rest_framework.authtoken.models import Token

            token, created = Token.objects.get_or_create(user=user)
            token_data = {"token": token.key, "token_type": "Token"}

        # Prepare user data (matching frontend User interface)
        user_data = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "fullName": user.fullName or user.name,
            "role": user.role,
            "avatarUrl": user.avatarUrl.url if user.avatarUrl else None,
            "companyId": user.companyId.id if user.companyId else None,
            "resellerId": user.resellerId.id if user.resellerId else None,
            "branchAccess": (
                list(user.branchAccess.values_list("id", flat=True))
                if user.branchAccess.exists()
                else []
            ),
            "status": user.status or "active",
            "lastLogin": (
                user.login_datetime.isoformat() if user.login_datetime else None
            ),
            "createdAt": user.created_at.isoformat() if user.created_at else None,
        }

        response_data = {
            "success": True,
            "user": user_data,
        }
        response_data.update(token_data)

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": "Login failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_user_profile(request):
    """
    Get current user profile - requires authentication
    """
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED
        )

    user = request.user
    user_data = {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "fullName": user.fullName or user.name,
        "role": user.role,
        "avatarUrl": user.avatarUrl.url if user.avatarUrl else None,
        "companyId": user.companyId.id if user.companyId else None,
        "resellerId": user.resellerId.id if user.resellerId else None,
        "branchAccess": (
            list(user.branchAccess.values_list("id", flat=True))
            if user.branchAccess.exists()
            else []
        ),
        "status": user.status or "active",
        "lastLogin": user.login_datetime.isoformat() if user.login_datetime else None,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
    }

    return Response({"success": True, "user": user_data}, status=status.HTTP_200_OK)


class RestaurantUserViewSet(viewsets.ModelViewSet):
    """
    Enhanced ViewSet for restaurant user management
    Provides comprehensive CRUD operations with RBAC support
    """

    serializer_class = UserManagementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter users based on requesting user's permissions"""
        queryset = GenUser.objects.select_related().prefetch_related("managed_branches")

        # Super users see all
        if self.request.user.is_superuser:
            return queryset

        # Software owners see all users
        if self.request.user.role == "software_owner":
            return queryset

        # Resellers see users in their managed companies
        if self.request.user.role == "reseller":
            if self.request.user.resellerId:
                return queryset.filter(resellerId=self.request.user.resellerId)

        # Company admins see users in their company
        if self.request.user.role in ["super_admin", "admin"]:
            if self.request.user.companyId:
                return queryset.filter(companyId=self.request.user.companyId)

        # Managers see users in their branches
        if self.request.user.role == "manager":
            if self.request.user.branchAccess:
                from utils.sqlite_compat import filter_users_by_branch_overlap

                try:
                    users = filter_users_by_branch_overlap(
                        queryset, self.request.user.branchAccess, check_active=False
                    )

                    if isinstance(users, list):
                        # For SQLite, we get a list, so filter the queryset by IDs
                        user_ids = [user.id for user in users]
                        return queryset.filter(id__in=user_ids)
                    else:
                        # For other databases, we get a queryset
                        return users
                except Exception:
                    # Fallback to showing only self if there's any error
                    return queryset.filter(id=self.request.user.id)

        # Default: users see only themselves
        return queryset.filter(id=self.request.user.id)

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == "create":
            return CreateRestaurantUserSerializer
        return UserManagementSerializer

    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Perform bulk operations on multiple users"""
        serializer = BulkUserUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        user_ids = validated_data["user_ids"]
        action_type = validated_data["action"]

        # Get users (filtered by permissions)
        users = self.get_queryset().filter(id__in=user_ids)
        if not users.exists():
            return Response(
                {"error": "No valid users found"}, status=status.HTTP_404_NOT_FOUND
            )

        updated_count = 0

        if action_type == "activate":
            updated_count = users.update(is_active=True, status="active")
        elif action_type == "deactivate":
            updated_count = users.update(is_active=False, status="inactive")
        elif action_type == "delete":
            updated_count = users.count()
            users.delete()
        elif action_type == "change_role":
            new_role = validated_data.get("new_role")
            if new_role:
                updated_count = users.update(role=new_role)
        elif action_type == "update_branch_access":
            raw_branch_access = validated_data.get("branch_access", [])
            branch_ids = [int(bid)
                          for bid in raw_branch_access if str(bid).isdigit()]

            from company.models import Branch

            branches = Branch.objects.filter(id__in=branch_ids, is_active=True)
            if branches.count() != len(branch_ids):
                return Response(
                    {"error": "Some branch IDs are invalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            updated_count = 0
            for user in users:
                user.branchAccess.set(branches)
                updated_count += 1

        return Response(
            {
                "success": True,
                "message": f"{updated_count} users updated successfully",
                "action": action_type,
            }
        )

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        """Reset user password"""
        user = self.get_object()
        new_password = request.data.get("new_password")

        if not new_password:
            return Response(
                {"error": "new_password is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.password_changes_datatime = timezone.now()
        user.save()

        return Response({"success": True, "message": "Password reset successfully"})

    @action(detail=True, methods=["post"])
    def toggle_status(self, request, pk=None):
        """Toggle user active status"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.status = "active" if user.is_active else "inactive"
        user.save()

        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def roles(self, request):
        """Get available user roles"""
        from .models import ROLE_CHOICE

        roles = [{"value": choice[0], "label": choice[1]}
                 for choice in ROLE_CHOICE]
        return Response(roles)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get user statistics"""
        queryset = self.get_queryset()

        stats = {
            "total_users": queryset.count(),
            "active_users": queryset.filter(is_active=True).count(),
            "inactive_users": queryset.filter(is_active=False).count(),
            "by_role": {},
            "recent_logins": queryset.filter(login_datetime__isnull=False)
            .order_by("-login_datetime")[:10]
            .values("id", "username", "fullName", "role", "login_datetime"),
        }

        # Count by role
        from .models import ROLE_CHOICE

        for role_code, role_name in ROLE_CHOICE:
            count = queryset.filter(role=role_code).count()
            if count > 0:
                stats["by_role"][role_code] = {
                    "name": role_name, "count": count}

        return Response(stats)

    @action(detail=False, methods=["get"])
    def by_company(self, request):
        """Get users grouped by company"""
        company_id = request.query_params.get("company_id")

        if company_id:
            users = self.get_queryset().filter(companyId=company_id)
        else:
            users = self.get_queryset()

        # Group by role within company
        users_by_role = {}
        for user in users:
            role = user.role or "unassigned"
            if role not in users_by_role:
                users_by_role[role] = []
            users_by_role[role].append(UserManagementSerializer(user).data)

        return Response(
            {
                "users_by_role": users_by_role,
                "total_users": users.count(),
                "company_id": company_id,
            }
        )

    @action(detail=False, methods=["get"])
    def by_branch(self, request):
        """Get users by branch access"""
        branch_id = request.query_params.get("branch_id")

        if not branch_id:
            return Response(
                {"error": "branch_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get users with access to this branch
        from utils.sqlite_compat import filter_users_by_branch_access

        users = filter_users_by_branch_access(
            self.get_queryset(), [branch_id], check_active=True
        )

        if isinstance(users, list):
            users_data = [UserManagementSerializer(
                user).data for user in users]
        else:
            users_data = UserManagementSerializer(users, many=True).data

        return Response(
            {
                "users": users_data,
                "total_users": len(users_data),
                "branch_id": branch_id,
            }
        )

    @action(detail=True, methods=["post"])
    def assign_branches(self, request, pk=None):
        """Assign branches to a user"""
        user = self.get_object()
        branch_ids = request.data.get("branch_ids", [])

        # Validate branch IDs
        if branch_ids:
            from company.models import Branch

            branches = Branch.objects.filter(id__in=branch_ids, is_active=True)
            if branches.count() != len(branch_ids):
                return Response(
                    {"error": "Some branch IDs are invalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Assign branches
        if branch_ids:
            user.branchAccess.set(branches)
        else:
            user.branchAccess.clear()

        serializer = self.get_serializer(user)
        return Response(
            {
                "message": f"User assigned to {len(branch_ids)} branches",
                "user": serializer.data,
            }
        )

    @action(detail=True, methods=["post"])
    def set_company(self, request, pk=None):
        """Assign user to a company"""
        user = self.get_object()
        company_id = request.data.get("company_id")

        if not company_id:
            return Response(
                {"error": "company_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate company exists
        from company.models import Company

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Assign company
        user.companyId = company  # Assign the actual Company instance
        user.company = company.name  # Keep legacy field for compatibility
        user.save()

        serializer = self.get_serializer(user)
        return Response(
            {
                "message": f"User assigned to company: {company.name}",
                "user": serializer.data,
            }
        )
