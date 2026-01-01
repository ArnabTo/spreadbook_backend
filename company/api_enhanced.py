import os

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import models
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Company, Branch
from .serializers import CompanyListSerializer, BranchSerializer
from authenticator.serializers import UserManagementSerializer
from utils.sqlite_compat import filter_users_by_branch_access
from utils import random as random_utils

User = get_user_model()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


def _generate_unique_branch_code() -> str:
    for _ in range(10):
        code = f"BR{random_utils.unique_code(6)}"
        if not Branch.objects.filter(code=code).exists():
            return code
    # fallback
    return f"BR{timezone.now().strftime('%H%M%S')}"


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def company_signup(request):
    """Signup endpoint: create a company + owner user + default branch.

    This supports SaaS onboarding:
    - New company starts on a free trial (DJANGO_TRIAL_DAYS, default 30)
    - nextBillingDate is set to trial end
    """

    try:
        company_name = (
            request.data.get("company_name") or request.data.get("name") or ""
        ).strip()
        owner_name = (
            request.data.get("owner_name") or request.data.get("ownerName") or ""
        ).strip()
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password")

        phone = (
            request.data.get("phone") or request.data.get("phoneNumber") or ""
        ).strip()
        full_address = (
            request.data.get("fullAddress") or request.data.get("address") or ""
        ).strip()
        city = (request.data.get("city") or "").strip() or None
        country = (request.data.get("country") or "Bangladesh").strip() or "Bangladesh"

        branch_name = (
            request.data.get("branch_name") or "Main Branch"
        ).strip() or "Main Branch"
        branch_address = (
            request.data.get("branch_fullAddress") or full_address or ""
        ).strip() or "-"

        if not company_name:
            return Response(
                {"success": False, "error": "company_name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not owner_name:
            return Response(
                {"success": False, "error": "owner_name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not email:
            return Response(
                {"success": False, "error": "email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not password:
            return Response(
                {"success": False, "error": "password is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"success": False, "error": "Email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now_dt = timezone.now()
        trial_days = _env_int("DJANGO_TRIAL_DAYS", 30)
        trial_ends = now_dt + timezone.timedelta(days=trial_days)

        # Create company
        company = Company.objects.create(
            name=company_name,
            email=email,
            ownerName=owner_name,
            phoneNumber=phone or None,
            phone=phone or None,
            fullAddress=full_address or None,
            address=full_address or None,
            city=city,
            country=country,
            subscriptionStatus="trial",
            trialEndsAt=trial_ends,
            nextBillingDate=trial_ends,
            daysOverdue=0,
            paymentType="monthly",
        )

        # Create default branch
        branch = Branch.objects.create(
            company=company,
            name=branch_name,
            code=_generate_unique_branch_code(),
            phoneNumber=phone or None,
            phone=phone or None,
            email=email,
            fullAddress=branch_address,
            location=branch_address,
            city=city,
            country=country,
            manager_name=owner_name,
        )

        # Create owner user
        # Use email as username for compatibility.
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
        )
        user.name = owner_name
        user.companyId = company
        user.role = "super_admin"
        user.status = "active"
        user.save(update_fields=["name", "companyId", "role", "status"])

        # Grant branch access (new model uses M2M)
        try:
            user.branchAccess.add(branch)
        except Exception:
            pass

        # In-app notification (best-effort)
        try:
            from common.models import Notification

            Notification.objects.create(
                company=company,
                user=user,
                type="success",
                title="Welcome! Trial started",
                message=f"Your free trial is active for {trial_days} days. It will end on {trial_ends.date().isoformat()}.",
                priority="medium",
                actionUrl="billing",
                actionLabel="Billing",
                data={"trialEndsAt": trial_ends.isoformat()},
            )
        except Exception:
            pass

        return Response(
            {
                "success": True,
                "message": "Signup successful",
                "company": CompanyListSerializer(company).data,
                "branch": BranchSerializer(branch).data,
                "user": UserManagementSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response(
            {"success": False, "error": "Signup failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_companies_with_branches(request):
    """
    Get all companies with their branches for the branch switcher
    Returns company data with associated branches
    """
    try:
        # Get user's access level
        user = request.user

        # Filter companies based on user permissions
        if user.role == "software_owner":
            companies = Company.objects.all()
        elif user.role == "reseller" and user.resellerId:
            companies = Company.objects.filter(resellerId=user.resellerId)
        elif user.role in ["super_admin", "admin"] and user.companyId:
            companies = Company.objects.filter(id=user.companyId_id)
        else:
            # For other users, show only their company
            companies = (
                Company.objects.filter(id=user.companyId_id)
                if user.companyId
                else Company.objects.none()
            )

        # Serialize companies with branch data
        companies_data = []
        for company in companies:
            company_serializer = CompanyListSerializer(company)
            company_data = company_serializer.data

            # Get branches for this company
            branches = company.company_branches.filter(is_active=True)

            # Filter branches based on user access
            if user.role not in ["software_owner", "reseller", "super_admin", "admin"]:
                if user.branchAccess.exists():
                    accessible_branch_ids = list(
                        user.branchAccess.values_list("id", flat=True)
                    )
                    branches = branches.filter(id__in=accessible_branch_ids)
                else:
                    branches = branches.none()

            branches_data = BranchSerializer(branches, many=True).data

            # Add company name to each branch for frontend compatibility
            for branch_data in branches_data:
                branch_data["companyName"] = company.name

            # Add branches to company data
            company_data["branches"] = branches_data
            companies_data.append(company_data)

        return Response(
            {"success": True, "companies": companies_data}, status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {
                "success": False,
                "error": "Failed to fetch companies and branches",
                "details": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_user_accessible_branches(request):
    """
    Get branches accessible to the current user
    """
    try:
        user = request.user

        # Get all branches if user has all access
        if user.role in ["software_owner", "reseller"]:
            branches = Branch.objects.filter(is_active=True)
        elif user.role in ["super_admin", "admin"] and user.companyId:
            # Company admins see all branches in their company
            branches = Branch.objects.filter(
                company_id=user.companyId_id, is_active=True
            )
        elif user.branchAccess.exists():
            # User has access to specific branches (ManyToMany)
            branches = user.branchAccess.filter(is_active=True)
            if user.companyId:
                branches = branches.filter(company_id=user.companyId_id)
        else:
            # No branch access defined
            branches = Branch.objects.none()

        # Group branches by company
        branches_by_company = {}
        for branch in branches.select_related("company"):
            company_id = str(branch.company.id)
            company_name = branch.company.name

            if company_id not in branches_by_company:
                branches_by_company[company_id] = {
                    "companyId": company_id,
                    "companyName": company_name,
                    "branches": [],
                }

            branch_data = BranchSerializer(branch).data
            branch_data["companyName"] = company_name
            branches_by_company[company_id]["branches"].append(branch_data)

        # Add company names to all branches as well
        all_branches_data = BranchSerializer(branches, many=True).data
        for branch_data in all_branches_data:
            # Find the corresponding branch to get company name
            branch_obj = next(
                (b for b in branches if str(b.id) == branch_data["id"]), None
            )
            if branch_obj:
                branch_data["companyName"] = branch_obj.company.name

        return Response(
            {
                "success": True,
                "branches_by_company": list(branches_by_company.values()),
                "all_branches": all_branches_data,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "success": False,
                "error": "Failed to fetch user accessible branches",
                "details": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def assign_user_to_branches(request):
    """
    Assign a user to specific branches
    Requires: user_id, branch_ids (array)
    """
    try:
        user_id = request.data.get("user_id")
        branch_ids = request.data.get("branch_ids", [])

        if not user_id:
            return Response(
                {"success": False, "error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the user to be assigned
        target_user = get_object_or_404(User, id=user_id)

        # Check permissions - only admins can assign users to branches
        requesting_user = request.user
        if requesting_user.role not in [
            "software_owner",
            "reseller",
            "super_admin",
            "admin",
        ]:
            return Response(
                {"success": False, "error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate branch IDs
        if branch_ids:
            branches = Branch.objects.filter(id__in=branch_ids, is_active=True)

            # If company admin, limit to their company
            if (
                requesting_user.role in ["super_admin", "admin"]
                and requesting_user.companyId
            ):
                branches = branches.filter(company_id=requesting_user.companyId_id)

            if branches.count() != len(branch_ids):
                return Response(
                    {"success": False, "error": "Some branch IDs are invalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            branches = Branch.objects.none()

        # Assign branches to user
        target_user.branchAccess.set(branches)

        # Return updated user data
        user_data = UserManagementSerializer(target_user).data

        return Response(
            {
                "success": True,
                "message": f"User assigned to {len(branch_ids)} branches",
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "success": False,
                "error": "Failed to assign user to branches",
                "details": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_branch_users(request, branch_id):
    """
    Get all users assigned to a specific branch
    """
    try:
        # Get the branch
        branch = get_object_or_404(Branch, id=branch_id)

        # Check permissions
        user = request.user
        if user.role not in [
            "software_owner",
            "reseller",
            "super_admin",
            "admin",
            "manager",
        ]:
            return Response(
                {"success": False, "error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get users with access to this branch
        users = filter_users_by_branch_access(
            User.objects.filter(is_active=True), [branch_id], check_active=True
        )

        # Include the branch manager if set
        if branch.manager and branch.manager not in users:
            if isinstance(users, list):
                users.append(branch.manager)
            else:
                # For queryset, we need to union
                manager_qs = User.objects.filter(id=branch.manager.id)
                users = users.union(manager_qs)

        # Serialize users
        if isinstance(users, list):
            users_data = [UserManagementSerializer(user).data for user in users]
        else:
            users_data = UserManagementSerializer(users, many=True).data

        return Response(
            {
                "success": True,
                "branch": BranchSerializer(branch).data,
                "users": users_data,
                "user_count": len(users_data),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "success": False,
                "error": "Failed to fetch branch users",
                "details": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_company_structure(request, company_id):
    """
    Get complete company structure with branches and users
    """
    try:
        # Get the company
        company = get_object_or_404(Company, id=company_id)

        # Check permissions
        user = request.user
        if user.role == "software_owner":
            pass  # Can access any company
        elif user.role == "reseller":
            if company.resellerId != user.resellerId:
                return Response(
                    {"success": False, "error": "Permission denied"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif user.companyId:
            if str(company.id) != str(user.companyId_id):
                return Response(
                    {"success": False, "error": "Permission denied"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            return Response(
                {"success": False, "error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get company data
        company_data = CompanyListSerializer(company).data

        # Get branches with user counts
        branches = company.company_branches.filter(is_active=True)
        branches_data = []

        for branch in branches:
            branch_data = BranchSerializer(branch).data

            # Get user count for this branch
            branch_users = filter_users_by_branch_access(
                User.objects.filter(is_active=True), [branch.id], check_active=True
            )
            branch_data["user_count"] = (
                len(branch_users)
                if isinstance(branch_users, list)
                else branch_users.count()
            )

            branches_data.append(branch_data)

        # Get total company users
        company_users = User.objects.filter(companyId=company_id, is_active=True)

        return Response(
            {
                "success": True,
                "company": company_data,
                "branches": branches_data,
                "total_users": company_users.count(),
                "total_branches": len(branches_data),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "success": False,
                "error": "Failed to fetch company structure",
                "details": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_user_with_branch_access(request):
    """
    Create a new user and assign them to specific branches
    """
    try:
        # Check permissions
        requesting_user = request.user
        if requesting_user.role not in [
            "software_owner",
            "reseller",
            "super_admin",
            "admin",
        ]:
            return Response(
                {"success": False, "error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Extract user data and branch assignments
        user_data = request.data.copy()
        branch_ids = user_data.pop("branch_ids", [])

        # Create user using existing serializer
        from authenticator.serializers import CreateRestaurantUserSerializer

        serializer = CreateRestaurantUserSerializer(data=user_data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": "Invalid user data",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save user
        user = serializer.save()

        # Assign branch access if provided
        if branch_ids:
            # Validate branch IDs
            branches = Branch.objects.filter(id__in=branch_ids, is_active=True)
            if branches.count() != len(branch_ids):
                return Response(
                    {"success": False, "error": "Some branch IDs are invalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.branchAccess.set(branches)

        # Return created user with branch info
        user_data = UserManagementSerializer(user).data

        return Response(
            {
                "success": True,
                "message": "User created successfully",
                "user": user_data,
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response(
            {"success": False, "error": "Failed to create user", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
