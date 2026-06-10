from rest_framework.decorators import permission_classes, action
from rest_framework.response import Response
from rest_framework import status
from django.db import models
from django.utils import timezone
from .models import Company, Branch, CompanyCustomization, Warehouse, Country, StateProvince
from .serializers import (
    CompanySerializer,
    CompanyListSerializer,
    BranchSerializer,
    CompanyCustomizationSerializer,
    WarehouseSerializer,
    CountrySerializer,
    StateProvinceSerializer,
    WarehouseDetailSerializer,
)
from rest_framework import serializers, viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import render, get_object_or_404
from datetime import datetime


def _add_months(dt: datetime, months: int) -> datetime:
    year = dt.year
    month = dt.month + months
    while month > 12:
        year += 1
        month -= 12
    while month < 1:
        year -= 1
        month += 12

    from calendar import monthrange

    last_day = monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day)


def _next_billing_date(now_dt: datetime, payment_type: str | None) -> datetime:
    pt = (payment_type or "monthly").lower()
    if pt == "yearly":
        return _add_months(now_dt, 12)
    if pt == "quarterly":
        return _add_months(now_dt, 3)
    return _add_months(now_dt, 1)


def _role(user) -> str:
    return (getattr(user, "role", "") or "").lower()


def _user_company_pk(user) -> int | None:
    """Return the user's company primary key as an int.

    In this codebase, `user.companyId` is a ForeignKey to Company, so `user.companyId`
    is usually a Company instance while `user.companyId_id` is the numeric PK.
    """

    company_id = getattr(user, "companyId_id", None)
    if isinstance(company_id, int):
        return company_id

    company_obj = getattr(user, "companyId", None)
    if company_obj is None:
        return None

    if isinstance(company_obj, int):
        return company_obj
    if isinstance(company_obj, str) and company_obj.isdigit():
        return int(company_obj)

    pk = getattr(company_obj, "pk", None)
    return pk if isinstance(pk, int) else None


def _company_queryset_for_user(user):
    """Return a Company queryset limited to the user's tenant scope."""
    role = _role(user)

    if role == "software_owner":
        return Company.objects.all()

    if role == "reseller" and getattr(user, "resellerId", None):
        return Company.objects.filter(resellerId=user.resellerId)

    company_pk = _user_company_pk(user)
    if role in {"super_admin", "admin"} and company_pk:
        return Company.objects.filter(id=company_pk)

    if company_pk:
        return Company.objects.filter(id=company_pk)

    return Company.objects.none()


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for all viewsets"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing companies
    Provides CRUD operations for companies with enhanced filtering and features
    """

    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "ownerName", "phoneNumber", "phone"]
    ordering_fields = [
        "name",
        "postedAt",
        "updateAt",
        "subscriptionPrice",
        "approvalStatus",
    ]
    ordering = ["-postedAt"]

    def get_queryset(self):
        queryset = _company_queryset_for_user(self.request.user).prefetch_related(
            "company_branches", "customization"
        )

        # Filter by subscription status
        subscription_status = self.request.query_params.get(
            "subscription_status", None)
        if subscription_status:
            queryset = queryset.filter(subscriptionStatus=subscription_status)

        # Filter by approval status
        approval_status = self.request.query_params.get(
            "approval_status", None)
        if approval_status:
            queryset = queryset.filter(approvalStatus=approval_status)

        # Filter by industry
        industry = self.request.query_params.get("industry", None)
        if industry:
            queryset = queryset.filter(industry=industry)

        # Filter by reseller
        reseller_id = self.request.query_params.get("reseller_id", None)
        if reseller_id:
            queryset = queryset.filter(resellerId=reseller_id)

        # Search by name, email, or owner name
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(ownerName__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == "list":
            return CompanyListSerializer
        return CompanySerializer

    @action(detail=True, methods=["get"])
    def branches(self, request, pk=None):
        """Get all branches for a specific company"""
        company = self.get_object()
        branches = company.branches.filter(is_active=True)
        serializer = BranchSerializer(branches, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "put"])
    def features(self, request, pk=None):
        """Get or update features for a specific company"""
        company = self.get_object()

        if request.method == "GET":
            return Response(company.features or [])

        elif request.method == "PUT":
            # Update features JSON field
            features_data = request.data.get("features", [])
            company.features = features_data
            company.save()
            return Response(features_data)

    @action(detail=True, methods=["get", "post", "put"])
    def customization(self, request, pk=None):
        """Get, create or update customization for a specific company"""
        company = self.get_object()

        if request.method == "GET":
            try:
                customization = company.customization
                # Return flattened structure matching frontend interface
                return Response(
                    {
                        "primaryColor": customization.primaryColor or "#007bff",
                        "currency": customization.currency or "USD",
                        "taxRate": float(customization.taxRate or 0.0),
                        "timezone": customization.timezone or "UTC",
                    }
                )
            except CompanyCustomization.DoesNotExist:
                return Response(
                    {
                        "primaryColor": "#007bff",
                        "currency": "USD",
                        "taxRate": 0.0,
                        "timezone": "UTC",
                    }
                )

        elif request.method in ["POST", "PUT"]:
            # Create or update customization with flattened data
            customization_data = {
                "primaryColor": request.data.get("primaryColor"),
                "currency": request.data.get("currency"),
                "taxRate": request.data.get("taxRate"),
                "timezone": request.data.get("timezone"),
            }

            # Remove None values
            customization_data = {
                k: v for k, v in customization_data.items() if v is not None
            }

            # Update or create customization
            customization, created = CompanyCustomization.objects.update_or_create(
                company=company, defaults=customization_data
            )

            # Return flattened response
            return Response(
                {
                    "primaryColor": customization.primaryColor or "#007bff",
                    "currency": customization.currency or "USD",
                    "taxRate": float(customization.taxRate or 0.0),
                    "timezone": customization.timezone or "UTC",
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a company"""
        company = self.get_object()
        approved_by = request.data.get("approved_by", "System")

        company.approvalStatus = "approved"
        company.approvalDate = timezone.now()
        company.approvedBy = approved_by

        # Update subscription status if initial payment is verified
        if company.initialPaymentStatus == "verified":
            company.subscriptionStatus = "active"
        else:
            company.subscriptionStatus = "pending_payment"

        company.save()

        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a company"""
        company = self.get_object()
        rejected_by = request.data.get("rejected_by", "System")
        rejection_reason = request.data.get("rejection_reason", "")

        company.approvalStatus = "rejected"
        company.approvalDate = timezone.now()
        company.approvedBy = rejected_by
        company.rejectionReason = rejection_reason
        company.subscriptionStatus = "cancelled"

        company.save()

        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def verify_payment(self, request, pk=None):
        """Verify initial payment for a company"""
        company = self.get_object()
        payment_details = request.data

        company.initialPaymentStatus = "verified"
        company.initialPaymentDate = payment_details.get(
            "payment_date", timezone.now())
        company.initialPaymentMethod = payment_details.get(
            "payment_method", "")
        company.initialPaymentTransactionId = payment_details.get(
            "transaction_id", "")
        company.lastPaymentDate = payment_details.get(
            "payment_date", timezone.now())

        # Update subscription status if company is approved
        if company.approvalStatus == "approved":
            company.subscriptionStatus = "active"

        company.save()

        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="record-subscription-payment")
    def record_subscription_payment(self, request, pk=None):
        """Record a renewal payment and automatically reactivate the account.

        This is a backend/manual entry point until a real payment gateway is integrated.
        """
        company = self.get_object()
        payment_date = request.data.get("payment_date")
        now_dt = timezone.now()

        # Parse optional date
        if payment_date:
            try:
                now_dt = timezone.make_aware(
                    datetime.fromisoformat(payment_date))
            except Exception:
                now_dt = timezone.now()

        company.lastPaymentDate = now_dt
        company.daysOverdue = 0
        company.subscriptionStatus = "active"
        company.nextBillingDate = _next_billing_date(
            now_dt, company.paymentType)
        company.save(
            update_fields=[
                "lastPaymentDate",
                "daysOverdue",
                "subscriptionStatus",
                "nextBillingDate",
            ]
        )

        # Create an in-app notification for company admins
        try:
            from authenticator.models import User
            from common.models import Notification

            admins = User.objects.filter(
                companyId=company,
                is_active=True,
                role__in=["admin", "super_admin", "manager"],
            ).only("id")
            if not admins.exists():
                admins = User.objects.filter(companyId=company, is_active=True).only(
                    "id"
                )

            key = f"sub_paid_{company.id}_{now_dt.date().isoformat()}"
            for u in admins:
                Notification.objects.get_or_create(
                    user=u,
                    dedupe_key=key,
                    defaults={
                        "company": company,
                        "type": "success",
                        "title": "Subscription payment received",
                        "message": "Your account is active and billing has been extended.",
                        "priority": "medium",
                        "actionUrl": "billing",
                        "actionLabel": "View Billing",
                        "data": {
                            "companyId": company.id,
                            "nextBillingDate": (
                                company.nextBillingDate.isoformat()
                                if company.nextBillingDate
                                else None
                            ),
                        },
                    },
                )
        except Exception:
            pass

        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        """Suspend a company subscription"""
        company = self.get_object()
        company.subscriptionStatus = "suspended"
        company.save()

        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        """Reactivate a suspended company"""
        company = self.get_object()
        company.subscriptionStatus = "active"
        company.save()

        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get company statistics"""
        total_companies = Company.objects.count()
        active_companies = Company.objects.filter(
            subscriptionStatus="active").count()
        pending_approval = Company.objects.filter(
            approvalStatus="pending").count()
        overdue_payments = Company.objects.filter(
            subscriptionStatus="payment_overdue"
        ).count()

        # Revenue statistics
        total_revenue = (
            Company.objects.aggregate(
                total=models.Sum("subscriptionPrice"))["total"]
            or 0
        )

        # Industry breakdown
        industry_stats = (
            Company.objects.values("industry")
            .annotate(count=models.Count("id"))
            .order_by("-count")
        )

        stats_data = {
            "total_companies": total_companies,
            "active_companies": active_companies,
            "pending_approval": pending_approval,
            "overdue_payments": overdue_payments,
            "total_monthly_revenue": total_revenue,
            "industry_breakdown": industry_stats,
        }

        return Response(stats_data)

    @action(detail=False, methods=["get"])
    def pending_approvals(self, request):
        """Get companies pending approval"""
        companies = (
            self.get_queryset().filter(approvalStatus="pending").order_by("postedAt")
        )
        serializer = CompanyListSerializer(companies, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def overdue_payments(self, request):
        """Get companies with overdue payments"""
        companies = (
            self.get_queryset()
            .filter(subscriptionStatus="payment_overdue")
            .order_by("lastPaymentDate")
        )
        serializer = CompanyListSerializer(companies, many=True)
        return Response(serializer.data)


class BranchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing restaurant branches
    Provides CRUD operations for branches
    """

    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "fullAddress", "city", "phoneNumber", "email"]
    ordering_fields = ["name", "postedAt", "updateAt", "city"]
    ordering = ["-postedAt"]

    def get_queryset(self):
        user = self.request.user
        role = _role(user)
        queryset = Branch.objects.select_related("company", "manager")

        if role != "software_owner":
            # Scope to reseller's companies
            if role == "reseller" and getattr(user, "resellerId", None):
                queryset = queryset.filter(company__resellerId=user.resellerId)
            else:
                # Scope to user's company
                company_pk = _user_company_pk(user)
                if company_pk:
                    queryset = queryset.filter(company_id=company_pk)
                else:
                    queryset = queryset.none()

            # Further restrict non-admin users to their branchAccess (if present)
            if role not in {"super_admin", "admin", "reseller"}:
                branch_access = getattr(user, "branchAccess", None)
                if branch_access:
                    # branchAccess is a ManyToManyField, need to call .all() to get queryset
                    accessible_branch_ids = list(
                        branch_access.all().values_list("id", flat=True)
                    )
                    if accessible_branch_ids:
                        queryset = queryset.filter(
                            id__in=accessible_branch_ids)

        # Filter by company if specified
        company_id = self.request.query_params.get("company", None)
        if company_id is not None:
            queryset = queryset.filter(company_id=company_id)

        # Filter by active status if specified
        is_active = self.request.query_params.get("active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter by city
        city = self.request.query_params.get("city", None)
        if city:
            queryset = queryset.filter(city__icontains=city)

        # Filter by country
        country = self.request.query_params.get("country", None)
        if country:
            queryset = queryset.filter(country__icontains=country)

        # Search by name or address
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(fullAddress__icontains=search)
                | models.Q(city__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        """Auto-assign company if user has company access"""
        # You can add logic here to auto-assign company based on user's company
        serializer.save()

    @action(detail=True, methods=["get"])
    def users(self, request, pk=None):
        """Get users assigned to this branch"""
        from authenticator.models import User
        from authenticator.serializers import UserSerializer
        from utils.sqlite_compat import filter_users_by_branch_access

        branch = self.get_object()
        users = filter_users_by_branch_access(
            User.objects, [branch.id], check_active=True
        )

        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def toggle_status(self, request, pk=None):
        """Toggle branch active status"""
        branch = self.get_object()
        branch.is_active = not branch.is_active
        branch.save()

        serializer = self.get_serializer(branch)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_company(self, request):
        """Get branches grouped by company"""
        company_id = request.query_params.get("company_id")
        if company_id:
            branches = Branch.objects.filter(
                company_id=company_id, is_active=True)
        else:
            branches = Branch.objects.filter(is_active=True)

        serializer = self.get_serializer(branches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get branch statistics"""
        total_branches = Branch.objects.count()
        active_branches = Branch.objects.filter(is_active=True).count()

        # Group by company
        company_stats = (
            Branch.objects.values("company__name")
            .annotate(
                branch_count=models.Count("id"),
                active_count=models.Count(
                    "id", filter=models.Q(is_active=True)),
            )
            .order_by("-branch_count")
        )

        # Group by city
        city_stats = (
            Branch.objects.values("city")
            .annotate(count=models.Count("id"))
            .order_by("-count")[:10]
        )  # Top 10 cities

        stats_data = {
            "total_branches": total_branches,
            "active_branches": active_branches,
            "branches_by_company": list(company_stats),
            "branches_by_city": list(city_stats),
        }

        return Response(stats_data)


class WarehouseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing warehouses (company => warehouse => branch)
    """

    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "fullAddress", "city", "code"]
    ordering_fields = ["name", "postedAt", "updateAt"]
    ordering = ["-postedAt"]

    def get_queryset(self):
        user = self.request.user
        role = _role(user)
        queryset = Warehouse.objects.select_related(
            "company", "manager", "parent_warehouse")

        if role != "software_owner":
            if role == "reseller" and getattr(user, "resellerId", None):
                queryset = queryset.filter(company__resellerId=user.resellerId)
            else:
                company_pk = _user_company_pk(user)
                if company_pk:
                    queryset = queryset.filter(company_id=company_pk)
                else:
                    queryset = queryset.none()

        # Filter by company
        company_id = self.request.query_params.get("company", None)
        if company_id is not None:
            queryset = queryset.filter(company_id=company_id)

        # Filter by active status
        is_active = self.request.query_params.get("active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter by parent warehouse
        parent_id = self.request.query_params.get("parent_warehouse", None)
        if parent_id is not None:
            queryset = queryset.filter(parent_warehouse_id=parent_id)

        return queryset

    @action(detail=True, methods=["get"])
    def branches(self, request, pk=None):
        """Get all branches connected to this warehouse"""
        warehouse = self.get_object()
        branches = warehouse.warehouse_branches.filter(is_active=True)
        serializer = BranchSerializer(branches, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        """Get child warehouses"""
        warehouse = self.get_object()
        children = warehouse.child_warehouses.filter(is_active=True)
        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def toggle_status(self, request, pk=None):
        """Toggle warehouse active status"""
        warehouse = self.get_object()
        warehouse.is_active = not warehouse.is_active
        warehouse.save()
        serializer = self.get_serializer(warehouse)
        return Response(serializer.data)


class CompanyCustomizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing company customizations
    Provides CRUD operations for company customizations
    """

    serializer_class = CompanyCustomizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        companies = _company_queryset_for_user(user)
        queryset = CompanyCustomization.objects.select_related("company").filter(
            company__in=companies
        )

        # Filter by company if specified
        company_id = self.request.query_params.get("company", None)
        if company_id is not None:
            queryset = queryset.filter(company_id=company_id)

        # Filter by currency
        currency = self.request.query_params.get("currency", None)
        if currency:
            queryset = queryset.filter(currency=currency)

        # Filter by timezone
        timezone_param = self.request.query_params.get("timezone", None)
        if timezone_param:
            queryset = queryset.filter(timezone__icontains=timezone_param)

        return queryset

    @action(detail=False, methods=["get"])
    def currency_stats(self, request):
        """Get currency usage statistics"""
        currency_stats = (
            CompanyCustomization.objects.values("currency")
            .annotate(count=models.Count("id"))
            .order_by("-count")
        )

        return Response(currency_stats)

    @action(detail=False, methods=["get"])
    def timezone_stats(self, request):
        """Get timezone usage statistics"""
        timezone_stats = (
            CompanyCustomization.objects.values("timezone")
            .annotate(count=models.Count("id"))
            .order_by("-count")
        )

        return Response(timezone_stats)

    @action(detail=True, methods=["post"])
    def reset_to_defaults(self, request, pk=None):
        """Reset customization to default values"""
        customization = self.get_object()

        customization.primaryColor = "#007bff"  # Default blue
        customization.currency = "USD"
        customization.taxRate = 0.0
        customization.timezone = "UTC"
        customization.save()

        serializer = self.get_serializer(customization)
        return Response(serializer.data)



class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.filter(is_active=True).order_by("name")
    serializer_class = CountrySerializer
    permission_classes = [permissions.IsAuthenticated]


class StateProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StateProvinceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StateProvince.objects.filter(is_active=True).select_related("country").order_by("name")
        country_id = self.request.query_params.get("country_id")
        if country_id:
            qs = qs.filter(country_id=country_id)
        return qs


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "city"]
    ordering_fields = ["name", "code", "city", "postedAt"]
    ordering = ["name"]

    def get_queryset(self):
        qs = Warehouse.objects.select_related("company", "country_ref", "state_ref").all()
        user = self.request.user
        from common.drf_scoping import is_unrestricted_user, get_company_ids_for_user
        if not is_unrestricted_user(user):
            company_ids = get_company_ids_for_user(user)
            if company_ids:
                qs = qs.filter(company_id__in=list(company_ids))
            else:
                return Warehouse.objects.none()
        return qs

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()
