from rest_framework.decorators import action
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from common.drf_scoping import (
    apply_company_branch_scope,
    get_allowed_branch_ids_for_user,
    get_company_ids_for_user,
    is_unrestricted_user,
)
from .models import Customer
from .serializers import CustomerSerializer
from .pagination import CustomerPagination


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customers with full CRUD operations
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer
    pagination_class = CustomerPagination
    filter_backends = [SearchFilter, OrderingFilter]

    # Search fields for the SearchFilter
    search_fields = [
        "name",
        "customer_code",
        "email",
        "phoneNumber",
        "fullAddress",
        "city",
        "company",
        "category",
        "notes",
    ]

    # Ordering fields
    ordering_fields = [
        "name",
        "created_at",
        "updated_at",
        "totalOrders",
        "totalSpent",
        "loyaltyPoints",
        "lastVisit",
        "category",
        "status",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Apply query parameter filters"""
        queryset = Customer.objects.all()

        # Apply query parameter filters
        category = self.request.query_params.get("category", None)
        status_filter = self.request.query_params.get("status", None)
        min_spent = self.request.query_params.get("min_spent", None)
        min_loyalty = self.request.query_params.get("min_loyalty", None)

        if category and category != "all":
            queryset = queryset.filter(category=category)

        if status_filter and status_filter != "all":
            queryset = queryset.filter(status=status_filter)

        if min_spent:
            try:
                min_spent_val = float(min_spent)
                queryset = queryset.filter(totalSpent__gte=min_spent_val)
            except ValueError:
                pass  # Ignore invalid values

        if min_loyalty:
            try:
                min_loyalty_val = int(min_loyalty)
                queryset = queryset.filter(loyaltyPoints__gte=min_loyalty_val)
            except ValueError:
                pass  # Ignore invalid values

        queryset = apply_company_branch_scope(
            request=self.request,
            queryset=queryset,
            company_id_field="companyId_id",
            branch_id_field="branch_id",
        )

        return queryset

    def _resolve_company(self):
        user = self.request.user
        if getattr(user, "companyId", None):
            return user.companyId

        branches = user.branchAccess.select_related("company")
        company_ids = set(branches.values_list("company_id", flat=True))
        if len(company_ids) == 1 and branches.exists():
            return branches.first().company

        return None

    def perform_create(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        company = self._resolve_company()
        if not company:
            raise PermissionDenied("User is not associated with a company")

        branch = serializer.validated_data.get("branch")
        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if branch is not None:
            if str(branch.company_id) != str(company.id):
                raise PermissionDenied("Branch does not belong to your company")
            if (
                allowed_branch_ids is not None
                and str(branch.id) not in allowed_branch_ids
            ):
                raise PermissionDenied("You do not have access to this branch")
        elif allowed_branch_ids is not None and len(allowed_branch_ids) == 1:
            branch_id = next(iter(allowed_branch_ids))
            branch = user.branchAccess.get(id=branch_id)

        serializer.save(companyId=company, branch=branch)

    def perform_update(self, serializer):
        user = self.request.user
        if is_unrestricted_user(user):
            serializer.save()
            return

        # Prevent cross-company reassignment
        company_ids = get_company_ids_for_user(user)
        if not company_ids or str(serializer.instance.companyId_id) not in company_ids:
            raise PermissionDenied("You do not have access to this customer")

        branch = serializer.validated_data.get("branch", serializer.instance.branch)
        allowed_branch_ids = get_allowed_branch_ids_for_user(user)
        if (
            branch is not None
            and allowed_branch_ids is not None
            and str(branch.id) not in allowed_branch_ids
        ):
            raise PermissionDenied("You do not have access to this branch")

        serializer.save(companyId=serializer.instance.companyId)

    def list(self, request, *args, **kwargs):
        """
        Override list method to ensure consistent pagination
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Fallback for non-paginated response
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Custom search endpoint with advanced filtering"""
        queryset = self.get_queryset()

        # Get search parameters
        search_query = request.query_params.get("search", "")
        category = request.query_params.get("category", "")
        status_filter = request.query_params.get("status", "")
        min_spent = request.query_params.get("min_spent", "")
        min_loyalty = request.query_params.get("min_loyalty", "")

        # Apply search across multiple fields
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(customer_code__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phoneNumber__icontains=search_query)
                | Q(fullAddress__icontains=search_query)
                | Q(company__icontains=search_query)
                | Q(notes__icontains=search_query)
            )

        # Apply category filter
        if category and category != "all":
            queryset = queryset.filter(category=category)

        # Apply status filter
        if status_filter and status_filter != "all":
            queryset = queryset.filter(status=status_filter)

        # Apply minimum spent filter
        if min_spent:
            try:
                min_spent_val = float(min_spent)
                queryset = queryset.filter(totalSpent__gte=min_spent_val)
            except ValueError:
                pass  # Ignore invalid values

        # Apply minimum loyalty points filter
        if min_loyalty:
            try:
                min_loyalty_val = int(min_loyalty)
                queryset = queryset.filter(loyaltyPoints__gte=min_loyalty_val)
            except ValueError:
                pass  # Ignore invalid values

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def toggle_status(self, request, pk=None):
        """Toggle customer status between Active/Inactive"""
        customer = self.get_object()

        # Toggle between Active and Inactive
        if customer.status == "Active":
            customer.status = "Inactive"
        else:
            customer.status = "Active"

        customer.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "message": "Customer status toggled successfully",
                "id": str(customer.id),
                "new_status": customer.status,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        """Override create to handle auto-generation of customer_code"""
        data = request.data.copy()

        # Auto-generate customer_code if not provided
        if not data.get("customer_code"):
            # Generate code like CUST001, CUST002, etc.
            last_customer = Customer.objects.all().order_by("customer_code").last()

            if (
                last_customer
                and last_customer.customer_code
                and last_customer.customer_code.startswith("CUST")
            ):
                try:
                    last_num = int(last_customer.customer_code[4:])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            data["customer_code"] = f"CUST{new_num:03d}"

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get customer statistics"""
        queryset = self.get_queryset()

        total_customers = queryset.count()
        active_customers = queryset.filter(status="Active").count()
        vip_customers = queryset.filter(category="vip").count()

        # Calculate totals
        total_revenue = sum(c.totalSpent or 0 for c in queryset)
        total_orders = sum(c.totalOrders or 0 for c in queryset)

        # Get category distribution
        categories = {}
        for category_choice in Customer.CATEGORY_CHOICES:
            category_key = category_choice[0]
            categories[category_key] = queryset.filter(category=category_key).count()

        return Response(
            {
                "totalCustomers": total_customers,
                "activeCustomers": active_customers,
                "vipCustomers": vip_customers,
                "totalRevenue": float(total_revenue),
                "totalOrders": total_orders,
                "averageSpent": (
                    float(total_revenue / total_customers) if total_customers > 0 else 0
                ),
                "categoryDistribution": categories,
            }
        )
