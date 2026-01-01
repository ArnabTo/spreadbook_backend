from rest_framework import serializers
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Expense, Category, ExpenseItem


class ExpenseItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ExpenseItem
        fields = "__all__"
        read_only_fields = ("expense_invoice",)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ExpenseListSerializer(serializers.ModelSerializer):
    """Serializer for expense list view with essential fields"""

    category_display = serializers.ReadOnlyField()
    status_display = serializers.ReadOnlyField()
    payment_method_display = serializers.ReadOnlyField()
    formatted_amount = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Expense
        fields = [
            "id",
            "expense_number",
            "category",
            "category_display",
            "description",
            "vendor",
            "amount",
            "formatted_amount",
            "payment_method",
            "payment_method_display",
            "status",
            "status_display",
            "recurring",
            "notes",
            "expense_date",
            "due_date",
            "is_overdue",
            "createdAt",
            "updatedAt",
        ]


class ExpenseDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for expense creation/update"""

    items = ExpenseItemSerializer(many=True, required=False)
    category_display = serializers.ReadOnlyField()
    status_display = serializers.ReadOnlyField()
    payment_method_display = serializers.ReadOnlyField()
    formatted_amount = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Expense
        fields = [
            "id",
            "expense_number",
            "category",
            "category_display",
            "description",
            "vendor",
            "amount",
            "formatted_amount",
            "payment_method",
            "payment_method_display",
            "status",
            "status_display",
            "recurring",
            "notes",
            "expense_date",
            "due_date",
            "is_overdue",
            "items",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = ("expense_number", "createdAt", "updatedAt")

    def create(self, validated_data):
        """Create expense with items if provided"""
        items_data = validated_data.pop("items", [])

        # Create the expense
        expense = Expense.objects.create(**validated_data)

        # Create items if provided
        for item_data in items_data:
            ExpenseItem.objects.create(expense_invoice=expense, **item_data)

        return expense

    def update(self, instance, validated_data):
        """Update expense and handle items"""
        items_data = validated_data.pop("items", [])

        # Update expense fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle items if provided
        if items_data is not None:
            keep_items = []

            for item_data in items_data:
                item_id = item_data.get("id")

                if (
                    item_id
                    and ExpenseItem.objects.filter(
                        id=item_id, expense_invoice=instance
                    ).exists()
                ):
                    # Update existing item
                    item = ExpenseItem.objects.get(id=item_id, expense_invoice=instance)
                    for attr, value in item_data.items():
                        if attr != "id":
                            setattr(item, attr, value)
                    item.save()
                    keep_items.append(item.id)
                else:
                    # Create new item
                    item_data.pop("id", None)  # Remove id if present
                    item = ExpenseItem.objects.create(
                        expense_invoice=instance, **item_data
                    )
                    keep_items.append(item.id)

            # Delete items not in the current list
            instance.items.exclude(id__in=keep_items).delete()

        return instance


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for expense creation matching frontend form"""

    class Meta:
        model = Expense
        fields = [
            "category",
            "description",
            "vendor",
            "amount",
            "payment_method",
            "status",
            "recurring",
            "notes",
            "expense_date",
            "due_date",
        ]

    def validate_amount(self, value):
        """Validate amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class ExpenseStatsSerializer(serializers.Serializer):
    """Statistics serializer for expense analytics with BDT currency"""

    total_expenses = serializers.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_expenses_bdt = serializers.SerializerMethodField()
    total_count = serializers.IntegerField(default=0)
    pending_count = serializers.IntegerField(default=0)
    paid_count = serializers.IntegerField(default=0)
    overdue_count = serializers.IntegerField(default=0)
    monthly_total = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_total_bdt = serializers.SerializerMethodField()
    weekly_total = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    weekly_total_bdt = serializers.SerializerMethodField()
    categories_breakdown = serializers.DictField(default=dict)
    payment_methods_breakdown = serializers.DictField(default=dict)
    currency = serializers.SerializerMethodField()

    def get_total_expenses_bdt(self, obj):
        """Format total expenses in BDT"""
        return f"৳{float(obj.get('total_expenses', 0)):,.2f}"

    def get_monthly_total_bdt(self, obj):
        """Format monthly total in BDT"""
        return f"৳{float(obj.get('monthly_total', 0)):,.2f}"

    def get_weekly_total_bdt(self, obj):
        """Format weekly total in BDT"""
        return f"৳{float(obj.get('weekly_total', 0)):,.2f}"

    def get_currency(self, obj):
        """Return currency code"""
        return "BDT"

    @staticmethod
    def get_stats():
        """Calculate expense statistics"""
        from django.db.models import Sum
        from datetime import datetime, timedelta

        now = timezone.now()

        # Basic counts and totals
        queryset = Expense.objects.all()
        total_expenses = queryset.aggregate(total=Sum("amount"))["total"] or 0
        total_count = queryset.count()

        # Status counts
        pending_count = queryset.filter(status="pending").count()
        paid_count = queryset.filter(status="paid").count()
        overdue_count = queryset.filter(
            due_date__lt=now.date(), status="pending"
        ).count()

        # Time-based totals
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_week = now - timedelta(days=now.weekday())

        monthly_total = (
            queryset.filter(expense_date__gte=start_of_month.date()).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        weekly_total = (
            queryset.filter(expense_date__gte=start_of_week.date()).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        # Category breakdown
        categories = (
            queryset.values("category")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        categories_breakdown = {
            item["category"]: {
                "total": float(item["total"]),
                "total_bdt": f"৳{float(item['total']):,.2f}",
                "count": item["count"],
            }
            for item in categories
        }

        # Payment method breakdown
        payment_methods = (
            queryset.values("payment_method")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        payment_methods_breakdown = {
            item["payment_method"]: {
                "total": float(item["total"]),
                "total_bdt": f"৳{float(item['total']):,.2f}",
                "count": item["count"],
            }
            for item in payment_methods
        }

        return {
            "total_expenses": total_expenses,
            "total_count": total_count,
            "pending_count": pending_count,
            "paid_count": paid_count,
            "overdue_count": overdue_count,
            "monthly_total": monthly_total,
            "weekly_total": weekly_total,
            "categories_breakdown": categories_breakdown,
            "payment_methods_breakdown": payment_methods_breakdown,
        }


# Legacy serializers for backward compatibility
class ExpenseSerializer(serializers.ModelSerializer):
    """Legacy expense serializer for backward compatibility"""

    items = ExpenseItemSerializer(many=True)

    class Meta:
        model = Expense
        fields = "__all__"

    def create(self, validated_data):
        """Legacy create method with old field names"""
        items_data = validated_data.pop("items", [])

        # Generate expense number (legacy format)
        last_expense = Expense.objects.all().order_by("createdAt").last()
        if not last_expense or not hasattr(last_expense, "expenseNumber"):
            new_expense_no = "EXP-0001"
        else:
            expense_number = getattr(last_expense, "expenseNumber", "EXP-0000")
            expense_int = int(expense_number.split("EXP-")[-1])
            new_expense_int = expense_int + 1
            new_expense_no = f"EXP-{new_expense_int:04d}"

        # Map old fields to new ones
        validated_data.pop("expenseNumber", None)
        if "expenseNumber" not in validated_data:
            validated_data["expense_number"] = new_expense_no

        expense_invoice = Expense.objects.create(**validated_data)

        # Create items
        for item_data in items_data:
            ExpenseItem.objects.create(expense_invoice=expense_invoice, **item_data)

        return expense_invoice


class ExpensePostSerializer(serializers.ModelSerializer):
    """Enhanced expense post serializer with BDT currency and itemwise functionality"""

    items = ExpenseItemSerializer(many=True, required=False)
    formatted_amount_bdt = serializers.SerializerMethodField()
    total_items_amount = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            "id",
            "expense_number",
            "category",
            "description",
            "vendor",
            "amount",
            "formatted_amount_bdt",
            "total_items_amount",
            "currency",
            "payment_method",
            "status",
            "recurring",
            "notes",
            "expense_date",
            "due_date",
            "items",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = (
            "expense_number",
            "createdAt",
            "updatedAt",
            "formatted_amount_bdt",
            "total_items_amount",
            "currency",
        )

    def get_formatted_amount_bdt(self, obj):
        """Return formatted amount in BDT"""
        return f"৳{obj.amount:,.2f}" if obj.amount else "৳0.00"

    def get_total_items_amount(self, obj):
        """Calculate total amount from items"""
        if hasattr(obj, "items"):
            total = sum(float(item.total or 0) for item in obj.items.all())
            return f"৳{total:,.2f}"
        return "৳0.00"

    def get_currency(self, obj):
        """Return currency code"""
        return "BDT"

    def validate_items(self, items_data):
        """Validate items data"""
        if not items_data:
            return items_data

        for item in items_data:
            if not item.get("title"):
                raise serializers.ValidationError("Item title is required")
            if not item.get("quantity") or item["quantity"] <= 0:
                raise serializers.ValidationError(
                    "Item quantity must be greater than 0"
                )
            if not item.get("price") or float(item["price"]) <= 0:
                raise serializers.ValidationError("Item price must be greater than 0")

        return items_data

    def validate_amount(self, value):
        """Validate amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value

    def create(self, validated_data):
        """Create expense with items and BDT currency support"""
        items_data = validated_data.pop("items", [])

        # Create the expense
        expense = Expense.objects.create(**validated_data)

        # Create items and calculate total if items provided
        total_from_items = 0
        for item_data in items_data:
            # Calculate item total
            quantity = item_data.get("quantity", 1)
            price = item_data.get("price", 0)
            item_total = float(quantity) * float(price)
            item_data["total"] = item_total
            total_from_items += item_total

            # Create the item
            ExpenseItem.objects.create(expense_invoice=expense, **item_data)

        # Update expense amount if calculated from items
        if items_data and total_from_items > 0:
            expense.amount = total_from_items
            expense.totalAmount = total_from_items
            expense.save()

        return expense

    def update(self, instance, validated_data):
        """Update expense with items"""
        items_data = validated_data.pop("items", None)

        # Update expense fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle items if provided
        if items_data is not None:
            # Clear existing items
            instance.items.all().delete()

            # Create new items and calculate total
            total_from_items = 0
            for item_data in items_data:
                quantity = item_data.get("quantity", 1)
                price = item_data.get("price", 0)
                item_total = float(quantity) * float(price)
                item_data["total"] = item_total
                total_from_items += item_total

                ExpenseItem.objects.create(expense_invoice=instance, **item_data)

            # Update expense amount
            if total_from_items > 0:
                instance.amount = total_from_items
                instance.totalAmount = total_from_items
                instance.save()

        return instance

    def to_representation(self, instance):
        """Custom representation with BDT formatting"""
        data = super().to_representation(instance)

        # Format all monetary values in BDT
        if "amount" in data and data["amount"]:
            data["amount_bdt"] = f"৳{float(data['amount']):,.2f}"

        # Format item amounts in BDT
        if "items" in data and data["items"]:
            for item in data["items"]:
                if item.get("price"):
                    item["price_bdt"] = f"৳{float(item['price']):,.2f}"
                if item.get("total"):
                    item["total_bdt"] = f"৳{float(item['total']):,.2f}"

        return data
