from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import MenuItem, MenuCategory


class MenuCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for MenuCategory model
    """

    class Meta:
        model = MenuCategory
        fields = [
            "id",
            "companyId",
            "branch",
            "name",
            "description",
            "is_active",
            "display_order",
        ]
        read_only_fields = ["id", "companyId"]


class MenuItemSerializer(serializers.ModelSerializer):
    """
    Serializer for MenuItem model with business logic
    """

    # Read-only calculated fields
    profit = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()
    markup_percentage = serializers.ReadOnlyField()

    # Optional fields for frontend compatibility
    id = serializers.UUIDField(read_only=True)
    item_code = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M")
    updated_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M")

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "companyId",
            "branch",
            "item_code",
            "name",
            "category",
            "price",
            "cost",
            "description",
            "short_description",
            "available",
            "is_featured",
            "preparation_time",
            "calories",
            "ingredients",
            "is_vegetarian",
            "is_vegan",
            "contains_gluten",
            "total_sold",
            "total_revenue",
            "display_order",
            "image",
            "profit",
            "profit_margin",
            "markup_percentage",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "companyId",
            "item_code",
            "profit",
            "profit_margin",
            "markup_percentage",
            "total_sold",
            "total_revenue",
            "created_at",
            "updated_at",
        ]

    def validate_price(self, value):
        """Validate price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value

    def validate_cost(self, value):
        """Validate cost is positive"""
        if value < 0:
            raise serializers.ValidationError("Cost cannot be negative")
        return value

    def validate(self, data):
        """Cross-field validation"""
        cost = data.get("cost", 0)
        price = data.get("price", 0)

        # If updating, get current values for fields not being updated
        if self.instance:
            cost = data.get("cost", self.instance.cost)
            price = data.get("price", self.instance.price)

        if cost >= price:
            raise serializers.ValidationError(
                {"cost": "Cost price must be less than selling price"}
            )

        return data

    def validate_name(self, value):
        """Validate menu item name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Menu item name is required")

        # Check for duplicate names in the same category
        if self.instance:
            # Updating existing item
            existing = MenuItem.objects.filter(
                name__iexact=value.strip(), category=self.instance.category
            ).exclude(id=self.instance.id)
        else:
            # Creating new item - we'll check category in validate method
            existing = MenuItem.objects.filter(name__iexact=value.strip())

        if existing.exists():
            raise serializers.ValidationError(
                "A menu item with this name already exists in this category"
            )

        return value.strip().title()


class MenuItemListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views
    """

    profit = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "item_code",
            "name",
            "category",
            "price",
            "cost",
            "description",
            "available",
            "is_featured",
            "total_sold",
            "profit",
            "profit_margin",
            "image",
            "created_at",
        ]


class MenuItemStatsSerializer(serializers.Serializer):
    """
    Serializer for menu item statistics
    """

    total_items = serializers.IntegerField()
    available_items = serializers.IntegerField()
    unavailable_items = serializers.IntegerField()
    featured_items = serializers.IntegerField()
    total_categories = serializers.IntegerField()

    # Financial stats
    total_revenue = serializers.FloatField()
    total_items_sold = serializers.IntegerField()
    average_price = serializers.FloatField()
    average_cost = serializers.FloatField()
    average_profit_margin = serializers.FloatField()

    # Category breakdown
    category_distribution = serializers.DictField()

    # Top performers
    top_selling_items = MenuItemListSerializer(many=True)
    most_profitable_items = MenuItemListSerializer(many=True)


class MenuItemBulkUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk operations
    """

    item_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=100
    )

    # Fields that can be bulk updated
    available = serializers.BooleanField(required=False)
    category = serializers.CharField(max_length=100, required=False)
    is_featured = serializers.BooleanField(required=False)

    def validate_item_ids(self, value):
        """Ensure all item IDs exist"""
        existing_ids = set(
            MenuItem.objects.filter(id__in=value).values_list("id", flat=True)
        )
        provided_ids = set(value)

        if existing_ids != provided_ids:
            missing_ids = provided_ids - existing_ids
            raise serializers.ValidationError(
                f"Menu items with IDs {list(missing_ids)} do not exist"
            )

        return value
