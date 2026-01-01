from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions, filters
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Expense, Category, ExpenseItem
from .serializers import (
    ExpenseListSerializer,
    ExpenseDetailSerializer,
    ExpenseCreateSerializer,
    ExpenseStatsSerializer,
    CategorySerializer,
    ExpenseItemSerializer,
    ExpenseSerializer,
    ExpensePostSerializer,  # Legacy serializers
)


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    Modern expense management viewset with filtering, search, and statistics
    """

    queryset = Expense.objects.all().order_by("-expense_date", "-createdAt")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["expense_number", "description", "vendor", "notes"]
    ordering_fields = ["expense_date", "amount", "createdAt", "updatedAt"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "list":
            return ExpenseListSerializer
        elif self.action == "create":
            return ExpenseCreateSerializer
        elif self.action in ["retrieve", "update", "partial_update"]:
            return ExpenseDetailSerializer
        return ExpenseDetailSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = self.queryset

        # Date range filtering
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                queryset = queryset.filter(expense_date__gte=start_date)
            except ValueError:
                pass

        if end_date:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                queryset = queryset.filter(expense_date__lte=end_date)
            except ValueError:
                pass

        # Amount range filtering
        min_amount = self.request.query_params.get("min_amount")
        max_amount = self.request.query_params.get("max_amount")

        if min_amount:
            try:
                queryset = queryset.filter(amount__gte=float(min_amount))
            except ValueError:
                pass

        if max_amount:
            try:
                queryset = queryset.filter(amount__lte=float(max_amount))
            except ValueError:
                pass

        # Overdue filtering
        if self.request.query_params.get("overdue") == "true":
            today = timezone.now().date()
            queryset = queryset.filter(due_date__lt=today, status="pending")

        return queryset

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get expense statistics"""
        stats = ExpenseStatsSerializer.get_stats()
        serializer = ExpenseStatsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def categories(self, request):
        """Get expense categories with totals (BDT formatted)"""
        categories = (
            Expense.objects.values("category")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        return Response(
            [
                {
                    "category": item["category"],
                    "total": item["total"],
                    "total_bdt": (
                        f"৳{float(item['total']):,.2f}" if item["total"] else "৳0.00"
                    ),
                    "count": item["count"],
                    "currency": "BDT",
                }
                for item in categories
            ]
        )

    @action(detail=False, methods=["get"])
    def monthly_summary(self, request):
        """Get monthly expense summary (BDT formatted)"""
        from django.db.models.functions import TruncMonth

        monthly_data = (
            Expense.objects.annotate(month=TruncMonth("expense_date"))
            .values("month")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-month")[:12]
        )  # Last 12 months

        return Response(
            [
                {
                    "month": item["month"].strftime("%Y-%m"),
                    "total": float(item["total"]),
                    "total_bdt": f"৳{float(item['total']):,.2f}",
                    "count": item["count"],
                    "currency": "BDT",
                }
                for item in monthly_data
            ]
        )

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        """Get overdue expenses"""
        today = timezone.now().date()
        overdue_expenses = self.queryset.filter(due_date__lt=today, status="pending")

        serializer = ExpenseListSerializer(overdue_expenses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        """Mark expense as paid"""
        expense = self.get_object()
        expense.status = "paid"
        expense.save()

        serializer = self.get_serializer(expense)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate an expense"""
        original_expense = self.get_object()

        # Create a copy of the expense
        expense_data = {
            "category": original_expense.category,
            "description": f"Copy of {original_expense.description}",
            "vendor": original_expense.vendor,
            "amount": original_expense.amount,
            "payment_method": original_expense.payment_method,
            "status": "pending",
            "recurring": original_expense.recurring,
            "notes": original_expense.notes,
            "expense_date": timezone.now().date(),
            "due_date": original_expense.due_date,
        }

        serializer = ExpenseCreateSerializer(data=expense_data)
        if serializer.is_valid():
            new_expense = serializer.save()

            # Copy items if any
            for item in original_expense.items.all():
                ExpenseItem.objects.create(
                    expense_invoice=new_expense,
                    title=item.title,
                    description=item.description,
                    quantity=item.quantity,
                    price=item.price,
                    total=item.total,
                )

            response_serializer = ExpenseDetailSerializer(new_expense)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryViewSet(viewsets.ModelViewSet):
    """Category management viewset"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


# Legacy ViewSets for backward compatibility
class ExpensetViewSet(viewsets.ModelViewSet):
    """Legacy expense viewset"""

    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class ExpensePostViewSet(viewsets.ModelViewSet):
    """Enhanced expense post viewset with BDT currency and itemwise functionality"""

    queryset = Expense.objects.all().order_by("-createdAt")
    serializer_class = ExpensePostSerializer

    def create(self, request, *args, **kwargs):
        """Create expense with enhanced BDT and itemwise support"""
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            expense = serializer.save()

            # Return enhanced response with BDT formatting
            response_data = serializer.to_representation(expense)
            response_data.update(
                {
                    "success": True,
                    "message": "Expense created successfully with BDT currency",
                    "currency": "BDT",
                    "expense_number": expense.expense_number,
                    "total_amount_bdt": f"৳{expense.amount:,.2f}",
                    "items_count": (
                        expense.items.count() if hasattr(expense, "items") else 0
                    ),
                }
            )

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(
            {
                "success": False,
                "message": "Validation failed",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def update(self, request, *args, **kwargs):
        """Update expense with BDT formatting"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            expense = serializer.save()

            response_data = serializer.to_representation(expense)
            response_data.update(
                {
                    "success": True,
                    "message": "Expense updated successfully",
                    "currency": "BDT",
                    "total_amount_bdt": f"৳{expense.amount:,.2f}",
                    "items_count": (
                        expense.items.count() if hasattr(expense, "items") else 0
                    ),
                }
            )

            return Response(response_data)

        return Response(
            {
                "success": False,
                "message": "Validation failed",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def list(self, request, *args, **kwargs):
        """List expenses with BDT formatting"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "currency": "BDT",
                "count": queryset.count(),
                "results": serializer.data,
            }
        )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve single expense with BDT formatting"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        response_data = serializer.data
        response_data.update({"success": True, "currency": "BDT"})

        return Response(response_data)
