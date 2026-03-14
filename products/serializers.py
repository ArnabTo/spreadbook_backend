from decimal import Clamped
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Category
from .models.product_model import (
    Product,
    NewLabel,
    SaleLabel,
    Size,
    Image,
    Tag,
    Color,
    ProductVariant,
    ProductSerialItem,
)
from .models.rating_model import Rating
from .models.review_model import Review
from .models.inventory_model import (
    InventoryItem,
    InventoryCategory,
    StockMovement,
    ProductStockMovement,
)
from .models import ProductType, GenericName, Brand, ProductBarcode, ProductBatch
from .models.unit_model import Unit
from suppliers.models import Supplier
from .function import attempt_json_deserialize

User = get_user_model()


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = "__all__"

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = "__all__"

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for product variants (size, color, quantity combinations)"""

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "unique_code",
            "size",
            "size_name",
            "size_code",
            "size_qty",
            "color",
            "price",
            "supplier_price",
            "image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "unique_code", "created_at", "updated_at"]

    def validate(self, data):
        """Ensure at least size or color is provided"""
        if not data.get("size") and not data.get("color"):
            raise serializers.ValidationError(
                "At least one of 'size' or 'color' must be provided for a variant."
            )
        return data


class NewLavelSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewLabel
        fields = ["pk", "enabled", "content"]

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class SaleLavelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleLabel
        fields = ["pk", "enabled", "content"]

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


# Update
class NewLavelUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewLabel
        fields = ["pk", "enabled", "content"]


class SaleLavelUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleLabel
        fields = ["pk", "enabled", "content"]


#


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ("id", "companyId", "created_at", "updated_at")

    def create(self, validated_data):
        """Auto-assign companyId from request context"""
        if "companyId" not in validated_data:
            request = self.context.get("request")
            if request and hasattr(request, "user") and request.user.is_authenticated:
                if hasattr(request.user, "companyId") and request.user.companyId:
                    validated_data["companyId"] = request.user.companyId
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class PictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = "__all__"

    def create(self, validated_data):
        image = Image.objects.create(**validated_data)
        # print(**validated_data)
        return image

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = [
            "name",
            "starCount",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    # category = CategorySerializer()
    newLabel = NewLavelSerializer(required=False)
    saleLabel = SaleLavelSerializer(required=False)
    # images = serializers.HyperlinkedRelatedField(many=True, view_name="product-detail", read_only=True, lookup_field="product-detail", )
    images = PictureSerializer(many=True, required=False)
    sizes = serializers.StringRelatedField(many=True, required=False)
    ratings = RatingSerializer(many=True, required=False)
    reviews = ReviewSerializer(many=True, required=False)
    tags = serializers.StringRelatedField(many=True, required=False)
    colors = serializers.StringRelatedField(many=True, required=False)
    variants = ProductVariantSerializer(
        many=True, required=False, read_only=True)

    # Dual-unit read-only helpers
    unit_name = serializers.CharField(
        source="unit.name", read_only=True, default=None)
    secondary_unit_name = serializers.CharField(
        source="secondary_unit.name", read_only=True, default=None
    )
    # Warehouse tracking read-only helpers
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default=None)

    class Meta:
        model = Product
        fields = "__all__"
        # Declare extra fields so they appear in the serialized output
        read_only_fields = ("unit_name", "secondary_unit_name",
                            "in_stock_secondary", "unique_code", "warehouse_name")

    def to_representation(self, instance):
        data = super().to_representation(instance)

        request = self.context.get("request")
        if not request:
            return data

        branch_id = request.query_params.get("branch_id") or request.query_params.get(
            "branchId"
        )
        if not branch_id:
            return data

        # Fast path: ProductViewSet prefetches a single-row list into this attr.
        inv_list = getattr(instance, "_branch_inventory_for_request", None)
        inv = inv_list[0] if isinstance(inv_list, list) and inv_list else None

        # Safe fallback (should be rare)
        if inv is None:
            try:
                from products.models import ProductBranchInventory

                inv = (
                    ProductBranchInventory.objects.filter(
                        product_id=getattr(instance, "id", None),
                        branch_id=branch_id,
                    )
                    .only(
                        "price",
                        "priceSale",
                        "regular_price",
                        "in_stock",
                        "available",
                    )
                    .first()
                )
            except Exception:
                inv = None

        if inv is None:
            # No per-branch override row yet.
            # - If Product is explicitly branch-scoped to this branch (legacy data), keep Product fields.
            # - If Product is shared (branch=NULL) or scoped to a different branch, the branch's stock is 0.
            try:
                product_branch_id = getattr(instance, "branch_id", None)
                if product_branch_id and str(product_branch_id) == str(branch_id):
                    return data

                data["in_stock"] = 0
                data["available"] = 0
                return data
            except Exception:
                return data

        # Override only the branch-scoped fields; keep shared catalog fields intact.
        data["price"] = inv.price
        data["priceSale"] = inv.priceSale
        data["regular_price"] = inv.regular_price
        data["in_stock"] = inv.in_stock
        data["available"] = inv.available
        return data

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class ProductPostSerializer(serializers.ModelSerializer):
    # category = serializers.StringRelatedField(many=True)
    newLabel = NewLavelUpdateSerializer(required=False)  # f
    saleLabel = SaleLavelUpdateSerializer(required=False)  # f
    # images = serializers.HyperlinkedRelatedField(many=True, view_name="product-detail", read_only=True, lookup_field="product-detail", )
    images = PictureSerializer(many=True, read_only=True)  # m
    # uploaded_images = serializers.ListField(
    #      child = serializers.ImageField(max_length = 1000000, allow_empty_file = False, use_url = False),
    #      write_only=True)
    sizes = SizeSerializer(many=True, required=False)
    ratings = RatingSerializer(many=True, required=False)
    reviews = ReviewSerializer(many=True, required=False)
    tags = TagSerializer(many=True, required=False)
    colors = ColorSerializer(many=True, required=False)

    # Variants support for clothing products
    variants = ProductVariantSerializer(
        many=True, required=False, read_only=False)

    # Dual-unit read-only helpers
    unit_name = serializers.CharField(
        source="unit.name", read_only=True, default=None)
    secondary_unit_name = serializers.CharField(
        source="secondary_unit.name", read_only=True, default=None
    )
    # Warehouse tracking read-only helpers
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default=None)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("unit_name", "secondary_unit_name",
                            "in_stock_secondary", "unique_code", "warehouse_name")

    def create(self, validated_data):
        from django.db import transaction

        # Extract nested data with defaults
        newlabel_data = validated_data.pop(
            "newLabel", {"enabled": False, "content": "New"}
        )
        salelabel_data = validated_data.pop(
            "saleLabel", {"enabled": False, "content": "Sale"}
        )
        variants_data = validated_data.pop("variants", [])

        # Use atomic transaction to ensure data consistency
        with transaction.atomic():
            # Create labels
            newLabel = NewLabel.objects.create(**newlabel_data)
            saleLabel = SaleLabel.objects.create(**salelabel_data)

            # Create product
            product = Product.objects.create(
                newLabel=newLabel, saleLabel=saleLabel, **validated_data
            )

            # Create variants if provided
            if variants_data:
                for variant_data in variants_data:
                    ProductVariant.objects.create(
                        product=product, **variant_data)

            # Seed a ProductBranchInventory row so per-branch stock/price lookups
            # work correctly from the moment the product is created.
            product_branch = getattr(product, "branch", None)
            if product_branch is not None:
                from products.branch_inventory import get_or_create_branch_inventory

                get_or_create_branch_inventory(product, product_branch)

        return product

    def update(self, instance, validated_data):
        from django.db import transaction

        newlabel_data = validated_data.pop("newLabel", None)
        salelabel_data = validated_data.pop("saleLabel", None)
        variants_data = validated_data.pop("variants", None)

        with transaction.atomic():
            # Existing rows may have NULL labels; avoid crashing on PATCH.
            if newlabel_data is not None:
                if instance.newLabel is None:
                    instance.newLabel = NewLabel.objects.create(
                        **newlabel_data)
                    instance.save(update_fields=["newLabel"])
                else:
                    newlabel_serializer = self.fields["newLabel"]
                    newlabel_serializer.update(
                        instance.newLabel, newlabel_data)

            if salelabel_data is not None:
                if instance.saleLabel is None:
                    instance.saleLabel = SaleLabel.objects.create(
                        **salelabel_data)
                    instance.save(update_fields=["saleLabel"])
                else:
                    salelabel_serializer = self.fields["saleLabel"]
                    salelabel_serializer.update(
                        instance.saleLabel, salelabel_data)

            # Handle variants update (replace all variants)
            if variants_data is not None:
                # Delete existing variants and create new ones
                instance.variants.all().delete()
                for variant_data in variants_data:
                    ProductVariant.objects.create(
                        product=instance, **variant_data)

            # Update product fields
            updated_instance = super().update(instance, validated_data)

        return updated_instance


class ProductTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductType
        fields = "__all__"


class GenericNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericName
        fields = "__all__"


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class ProductBarcodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductBarcode
        fields = "__all__"


class ProductBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductBatch
        fields = "__all__"


# class ProductSerializer(serializers.ModelSerializer):
#      # category = serializers.StringRelatedField(many=True)
#      newLabel = NewLavelSerializer(required=False) #f
#      saleLabel = SaleLavelSerializer(required=False) #f
#      # images = serializers.HyperlinkedRelatedField(many=True, view_name="product-detail", read_only=True, lookup_field="product-detail", )
#      images = PictureSerializer(many=True, read_only=True) #m
#      uploaded_images = serializers.ListField(
#           child = serializers.ImageField(max_length = 1000000, allow_empty_file = False, use_url = False),
#           write_only=True)
#      sizes = SizeSerializer(many=True, required=False) #mt
#      # ratings = RatingSerializer(many = True, required=False)
#      # reviews = ReviewSerializer(many = True, required=False)
#      # tags = serializers.StringRelatedField(many = True, required=False)
#      # colors = serializers.StringRelatedField(many=True, required=False)

#      class Meta:
#           model = Product
#           fields = '__all__'


#      def create(self, validated_data):
#           uploaded_images = validated_data.pop("uploaded_images")
#           # newlabel_data = validated_data.pop('newLabel')
#           # salelabel_data = validated_data.pop('saleLabel')
#           # print(images_data)
#           # newLabel, created = NewLabel.objects.get_or_create(**newlabel_data)
#           # saleLabel, created = SaleLabel.objects.get_or_create(**salelabel_data)

#           product = Product.objects.create(**validated_data)
#           for imgae in uploaded_images:
#                newproduct_image = Image.objects.create(product=product, picture=imgae)

#           return product


class ProductImagePostSerializer(serializers.ModelSerializer):
    # category = serializers.StringRelatedField(many=True)
    # newLabel = NewLavelSerializer() #f
    # saleLabel = SaleLavelSerializer() #f
    # images = serializers.HyperlinkedRelatedField(many=True, view_name="product-detail", read_only=True, lookup_field="product-detail", )
    images = PictureSerializer(many=True, read_only=True)  # m
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(
            max_length=1000000, allow_empty_file=False, use_url=False
        ),
        write_only=True,
    )
    # sizes = SizeSerializer(many=True, required=False) #mt
    # ratings = RatingSerializer(many = True, required=False)
    # reviews = ReviewSerializer(many = True, required=False)
    # tags = TagSerializer(many = True, required=False)
    # colors = ColorSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = "__all__"

    # def create(self, validated_data):
    #      uploaded_images = validated_data.pop("uploaded_images")
    #      for imgae in uploaded_images:
    #           newproduct_image = Image.objects.create(product=product, picture=imgae)

    #      return newproduct_image


# Inventory Management Serializers


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ["id", "name", "status"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "phone", "email", "address"]


class InventoryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCategory
        fields = ["id", "name", "description", "is_active"]


class InventoryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    supplier_name = serializers.CharField(
        source="supplier.name", read_only=True)
    status_display = serializers.CharField(
        source="get_status_display", read_only=True)
    formatted_last_updated = serializers.CharField(read_only=True)
    stock_percentage = serializers.FloatField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "category",
            "category_name",
            "unit",
            "unit_name",
            "current_stock",
            "reorder_level",
            "max_stock",
            "cost_per_unit",
            "total_value",
            "supplier",
            "supplier_name",
            "status",
            "status_display",
            "last_updated",
            "formatted_last_updated",
            "stock_percentage",
            "is_low_stock",
            "sku",
            "description",
            "location",
            "expiry_date",
            "warranty_expiry_date",
            "notes",
            "average_usage",
        ]


class InventoryItemCreateUpdateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "category",
            "unit",
            "current_stock",
            "reorder_level",
            "max_stock",
            "cost_per_unit",
            "supplier",
            "sku",
            "description",
            "location",
            "expiry_date",
            "warranty_expiry_date",
            "notes",
            "average_usage",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(
        source="inventory_item.name", read_only=True
    )
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "inventory_item",
            "inventory_item_name",
            "movement_type",
            "movement_type_display",
            "quantity",
            "previous_stock",
            "new_stock",
            "reason",
            "notes",
            "reference_number",
            "created_at",
            "created_by",
        ]


class AddStockSerializer(serializers.Serializer):
    """Serializer for adding stock to inventory items"""

    quantity = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0.01)
    reason = serializers.CharField(
        max_length=200, required=False, default="Stock addition"
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    reference_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    expiry_date = serializers.DateField(required=False, allow_null=True)
    warranty_expiry_date = serializers.DateField(
        required=False, allow_null=True)


class InventoryStatsSerializer(serializers.Serializer):
    """Serializer for inventory statistics"""

    total_items = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    categories_count = serializers.IntegerField()
    out_of_stock_count = serializers.IntegerField()


class ProductStockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )

    class Meta:
        model = ProductStockMovement
        fields = [
            "id",
            "product",
            "product_name",
            "movement_type",
            "movement_type_display",
            "quantity",
            "previous_stock",
            "new_stock",
            "reason",
            "notes",
            "reference_number",
            "created_at",
            "created_by",
        ]


class ProductSerialItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name", read_only=True, default=None
    )
    variant_info = serializers.SerializerMethodField()
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default=None
    )
    branch_name = serializers.CharField(
        source="branch.name", read_only=True, default=None
    )

    class Meta:
        model = ProductSerialItem
        fields = "__all__"
        read_only_fields = ("serial_code", "created_at", "updated_at")

    def get_variant_info(self, obj):
        if not obj.variant:
            return None
        return {
            "id": str(obj.variant.id),
            "size": obj.variant.size,
            "color": obj.variant.color,
            "unique_code": obj.variant.unique_code,
        }
