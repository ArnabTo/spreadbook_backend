from rest_framework.decorators import permission_classes, action
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from company.models import Branch
from .models import Supplier, SupplierCategory
from .serializers import SupplierSerializer, SupplierCategorySerializer
from .pagination import SupplierPagination
from rest_framework import viewsets, permissions
from rest_framework.filters import SearchFilter, OrderingFilter


class SupplierCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Supplier Categories
    Supports CRUD operations for supplier categories scoped by company
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SupplierCategorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "is_active"]
    ordering = ["name"]

    def _get_allowed_branch_ids(self, user):
        if self._is_unrestricted_user(user):
            return None
        if user.branchAccess.exists():
            return set(user.branchAccess.values_list("id", flat=True))
        return None

    def _resolve_company_from_branch(self, user):
        branch_id = self.request.data.get("branch_id") or self.request.query_params.get(
            "branch_id"
        )
        if not branch_id:
            return None

        allowed_branch_ids = self._get_allowed_branch_ids(user)
        if allowed_branch_ids is not None and str(branch_id) not in {
            str(b) for b in allowed_branch_ids
        }:
            raise PermissionDenied("You do not have access to this branch")

        branch = Branch.objects.select_related("company").filter(id=branch_id).first()
        if not branch:
            raise PermissionDenied("Invalid branch_id")

        return branch.company

    def _is_unrestricted_user(self, user) -> bool:
        return (
            bool(getattr(user, "is_superuser", False))
            or getattr(user, "role", None) == "software_owner"
        )

    def _resolve_company(self, user):
        if getattr(user, "companyId", None):
            return user.companyId

        # Fallback: infer company from branch access if possible
        branches = user.branchAccess.select_related("company")
        company_ids = set(branches.values_list("company_id", flat=True))
        if len(company_ids) == 1 and branches.exists():
            return branches.first().company

        return None

    def get_queryset(self):
        user = self.request.user
        queryset = SupplierCategory.objects.all()

        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            company_from_branch = self._resolve_company_from_branch(user)
            if company_from_branch:
                queryset = queryset.filter(companyId=company_from_branch)
                is_active = self.request.query_params.get("is_active")
                if is_active is not None:
                    queryset = queryset.filter(is_active=is_active.lower() == "true")
                return queryset.select_related("companyId").prefetch_related(
                    "suppliers"
                )

        if not self._is_unrestricted_user(user):
            # Company scoping (multi-tenant safety)
            company_ids = set()
            if getattr(user, "companyId_id", None):
                company_ids.add(user.companyId_id)
            else:
                company_ids.update(
                    user.branchAccess.values_list("company_id", flat=True)
                )

            if not company_ids:
                return SupplierCategory.objects.none()

            queryset = queryset.filter(companyId_id__in=company_ids)

        # Filter by is_active if requested
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.select_related("companyId").prefetch_related("suppliers")

    def perform_create(self, serializer):
        """Auto-assign company from selected branch, fallback to authenticated user company"""
        user = self.request.user
        company = self._resolve_company_from_branch(user) or self._resolve_company(user)

        if not company:
            raise PermissionDenied(
                "Unable to determine company. Provide a valid branch_id or ensure user has company access"
            )

        serializer.save(companyId=company)

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get only active categories for the user's company"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SupplierViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SupplierSerializer
    pagination_class = SupplierPagination
    filter_backends = [SearchFilter, OrderingFilter]

    def _is_unrestricted_user(self, user) -> bool:
        return (
            bool(getattr(user, "is_superuser", False))
            or getattr(user, "role", None) == "software_owner"
        )

    def _resolve_company(self, user):
        if getattr(user, "companyId", None):
            return user.companyId

        # Fallback: infer company from branch access if possible
        branches = user.branchAccess.select_related("company")
        company_ids = set(branches.values_list("company_id", flat=True))
        if len(company_ids) == 1 and branches.exists():
            return branches.first().company

        return None

    def _get_allowed_branch_ids(self, user):
        if self._is_unrestricted_user(user):
            return None
        if user.branchAccess.exists():
            return set(user.branchAccess.values_list("id", flat=True))
        return None

    # Search fields for the SearchFilter
    search_fields = [
        "name",
        "supplier_code",
        "email",
        "phone",
        "address",
        "country",
        "contactPerson",
        "category__name",
    ]

    # Ordering fields
    ordering_fields = [
        "name",
        "created_at",
        "updated_at",
        "rating",
        "totalSpent",
        "category__name",
        "status",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        queryset = Supplier.objects.select_related(
            "category", "companyId"
        ).prefetch_related("branchId")

        requested_company_id = self.request.query_params.get(
            "company_id"
        ) or self.request.query_params.get("companyId")

        if not self._is_unrestricted_user(user):
            # Company scoping (multi-tenant safety)
            company_ids = set()
            if getattr(user, "companyId_id", None):
                company_ids.add(user.companyId_id)
            else:
                company_ids.update(
                    user.branchAccess.values_list("company_id", flat=True)
                )

            if not company_ids:
                return Supplier.objects.none()

            if requested_company_id:
                if str(requested_company_id) not in {str(cid) for cid in company_ids}:
                    raise PermissionDenied("You do not have access to this company")
                queryset = queryset.filter(companyId_id=requested_company_id)
            else:
                queryset = queryset.filter(companyId_id__in=company_ids)

            # Optional branch scoping when branchAccess is explicitly assigned.
            # If explicit company filtering is requested, keep result company-wise.
            if not requested_company_id:
                allowed_branch_ids = self._get_allowed_branch_ids(user)
                branch_id = self.request.query_params.get(
                    "branch_id"
                ) or self.request.query_params.get("branchId")
                if branch_id:
                    if allowed_branch_ids is not None and branch_id not in {
                        str(b) for b in allowed_branch_ids
                    }:
                        raise PermissionDenied("You do not have access to this branch")
                    queryset = queryset.filter(branchId__id=branch_id)
                elif allowed_branch_ids is not None:
                    queryset = queryset.filter(
                        Q(branchId__id__in=allowed_branch_ids)
                        | Q(branchId__isnull=True)
                    )

            queryset = queryset.distinct()

        # Apply query parameter filters
        category = self.request.query_params.get("category", None)
        status_filter = self.request.query_params.get("status", None)
        min_rating = self.request.query_params.get("min_rating", None)

        if category and category != "all":
            # Support both category ID and name filtering
            queryset = queryset.filter(
                Q(category__id=category) | Q(category__name__iexact=category)
            )

        if status_filter and status_filter != "all":
            queryset = queryset.filter(status=status_filter)

        if min_rating:
            try:
                min_rating_val = float(min_rating)
                queryset = queryset.filter(rating__gte=min_rating_val)
            except ValueError:
                pass  # Ignore invalid rating values

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if self._is_unrestricted_user(user):
            serializer.save()
            return

        company = self._resolve_company(user)
        if not company:
            raise PermissionDenied("User is not associated with a company")

        serializer.save(companyId=company)

    def perform_update(self, serializer):
        user = self.request.user
        if self._is_unrestricted_user(user):
            serializer.save()
            return

        # Prevent cross-company reassignment even if payload includes companyId
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

        # Fallback for non-paginated response (shouldn't happen with pagination enabled)
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
        min_rating = request.query_params.get("min_rating", "")

        # Apply search across multiple fields
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(supplier_code__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phone__icontains=search_query)
                | Q(address__icontains=search_query)
                | Q(contactPerson__icontains=search_query)
                | Q(category__icontains=search_query)
            )

        # Apply category filter
        if category and category != "all":
            queryset = queryset.filter(category=category)

        # Apply status filter
        if status_filter and status_filter != "all":
            queryset = queryset.filter(status=status_filter)

        # Apply rating filter
        if min_rating:
            try:
                min_rating_val = float(min_rating)
                queryset = queryset.filter(rating__gte=min_rating_val)
            except ValueError:
                pass  # Ignore invalid rating values

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def toggle_status(self, request, pk=None):
        """Toggle supplier status between Active/Inactive"""
        supplier = self.get_object()

        # Toggle between Active and Inactive
        if supplier.status == "Active":
            supplier.status = "Inactive"
        else:
            supplier.status = "Active"

        supplier.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "message": "Supplier status toggled successfully",
                "id": str(supplier.id),
                "new_status": supplier.status,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        """Override create to handle auto-generation of supplier_code"""
        data = request.data.copy()

        # Auto-generate supplier_code if not provided
        if not data.get("supplier_code"):
            # Generate code like SUP001, SUP002, etc.
            # For authenticated users with company, scope to company
            if (
                request.user.is_authenticated
                and hasattr(request.user, "company")
                and request.user.company
            ):
                last_supplier = (
                    Supplier.objects.filter(companyId=request.user.company)
                    .order_by("supplier_code")
                    .last()
                )
            else:
                # For anonymous users, use global scope
                last_supplier = Supplier.objects.all().order_by("supplier_code").last()

            if (
                last_supplier
                and last_supplier.supplier_code
                and last_supplier.supplier_code.startswith("SUP")
            ):
                try:
                    last_num = int(last_supplier.supplier_code[3:])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            data["supplier_code"] = f"SUP{new_num:03d}"

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get supplier statistics"""
        queryset = self.get_queryset()

        total_suppliers = queryset.count()
        active_suppliers = queryset.filter(status="Active").count()
        inactive_suppliers = queryset.filter(status="Inactive").count()
        suspended_suppliers = queryset.filter(status="Suspended").count()

        # Calculate average rating
        ratings = queryset.exclude(rating=0).values_list("rating", flat=True)
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        # Get category distribution
        categories = {}
        for supplier in queryset.values("category").distinct():
            category = supplier["category"]
            categories[category] = queryset.filter(category=category).count()

        return Response(
            {
                "totalSuppliers": total_suppliers,
                "activeSuppliers": active_suppliers,
                "inactiveSuppliers": inactive_suppliers,
                "suspendedSuppliers": suspended_suppliers,
                "averageRating": round(avg_rating, 2),
                "categoryDistribution": categories,
            }
        )

    @action(detail=False, methods=["get"])
    def export(self, request):
        """Export suppliers data - exports all data without pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        format_type = request.query_params.get("format", "csv")

        # Add limit for export to prevent large exports
        max_export_limit = 10000
        if queryset.count() > max_export_limit:
            return Response(
                {
                    "error": f"Export limited to {max_export_limit} records. Please apply filters to reduce the dataset."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if format_type == "csv":
            import csv
            from django.http import HttpResponse

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="suppliers.csv"'

            writer = csv.writer(response)
            writer.writerow(
                [
                    "ID",
                    "Name",
                    "Code",
                    "Category",
                    "Contact Person",
                    "Email",
                    "Phone",
                    "Address",
                    "Status",
                    "Rating",
                    "Total Spent",
                    "Payment Terms",
                ]
            )

            for supplier in queryset:
                writer.writerow(
                    [
                        str(supplier.id),
                        supplier.name,
                        supplier.supplier_code,
                        supplier.category,
                        supplier.contactPerson or "",
                        supplier.email,
                        str(supplier.phone),
                        supplier.address,
                        supplier.status,
                        str(supplier.rating),
                        str(supplier.totalSpent),
                        supplier.paymentTerms,
                    ]
                )

            return response

        # Default to JSON export
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
