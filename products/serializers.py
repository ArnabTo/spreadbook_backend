from decimal import Clamped
import logging
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
    UnitConversionGroup,
    UnitConversionStep,
)
from .models.inventory_model import (
    InventoryItem,
    InventoryCategory,
    StockMovement,
    ProductStockMovement,
    ProductBranchInventory,
)
from .models.rating_model import Rating
from .models.review_model import Review
from .models.stock_transfer_model import StockTransfer, StockTransferItem
from .models import ProductType, GenericName, Brand, ProductBarcode, ProductBatch
from .models.unit_model import Unit
from suppliers.models import Supplier
from .function import attempt_json_deserialize

logger = logging.getLogger(__name__)

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
    variants = ProductVariantSerializer(many=True, required=False, read_only=True)

    # Dual-unit read-only helpers
    unit_name = serializers.CharField(source="unit.name", read_only=True, default=None)
    secondary_unit_name = serializers.CharField(
        source="secondary_unit.name", read_only=True, default=None
    )
    unit_conversion_group_name = serializers.CharField(
        source="unit_conversion_group.name", read_only=True, default=None
    )
    display_unit_name = serializers.CharField(
        source="display_unit.name", read_only=True, default=None
    )
    # Selling unit read-only helpers
    selling_unit_name = serializers.CharField(
        source="selling_unit.name", read_only=True, default=None
    )
    # Warehouse tracking read-only helpers
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default=None
    )

    class Meta:
        model = Product
        fields = "__all__"
        # Declare extra fields so they appear in the serialized output
        read_only_fields = (
            "unit_name",
            "secondary_unit_name",
            "unit_conversion_group_name",
            "display_unit_name",
            "selling_unit_name",
            "in_stock_secondary",
            "unique_code",
            "warehouse_name",
        )

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
                        "quantity",
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
        data["in_stock"] = int(inv.quantity or 0)
        data["available"] = int(inv.quantity or 0)
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
    variants = ProductVariantSerializer(many=True, required=False, read_only=False)

    # Dual-unit read-only helpers
    unit_name = serializers.CharField(source="unit.name", read_only=True, default=None)
    secondary_unit_name = serializers.CharField(
        source="secondary_unit.name", read_only=True, default=None
    )
    unit_conversion_group_name = serializers.CharField(
        source="unit_conversion_group.name", read_only=True, default=None
    )
    display_unit_name = serializers.CharField(
        source="display_unit.name", read_only=True, default=None
    )
    # Selling unit read-only helpers
    selling_unit_name = serializers.CharField(
        source="selling_unit.name", read_only=True, default=None
    )

    # Unit conversion fields - explicitly defined to ensure proper handling in updates
    unit_conversion_group = serializers.PrimaryKeyRelatedField(
        queryset=UnitConversionGroup.objects.all(),
        required=False,
        allow_null=True,
        help_text="Conversion rule set used for this product",
    )
    display_unit = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(),
        required=False,
        allow_null=True,
        help_text="Preferred unit for UI/API display",
    )
    selling_unit = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.all(),
        required=False,
        allow_null=True,
        help_text="The unit in which customers buy this product",
    )
    selling_unit_conversion_factor = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=1,
        help_text="How many selling units equal 1 base unit",
    )
    # Warehouse tracking read-only helpers
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default=None
    )

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = (
            "unit_name",
            "secondary_unit_name",
            "unit_conversion_group_name",
            "display_unit_name",
            "selling_unit_name",
            "in_stock_secondary",
            "unique_code",
            "warehouse_name",
        )

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

        # Pop stock fields from product payload — stock is managed exclusively
        # via StockSummary. Product.in_stock will be auto-recalculated by signal.
        initial_stock = validated_data.pop("in_stock", 0) or 0
        validated_data.pop("available", None)
        # quantity (max_capacity) stays on the Product model; it is not stock.

        # Use atomic transaction to ensure data consistency
        with transaction.atomic():
            # Create labels
            newLabel = NewLabel.objects.create(**newlabel_data)
            saleLabel = SaleLabel.objects.create(**salelabel_data)

            # Create product with in_stock=0; signal will set it from StockSummary.
            product = Product.objects.create(
                newLabel=newLabel, saleLabel=saleLabel, in_stock=0, **validated_data
            )

            company = product.companyId
            warehouse = product.warehouse
            branch = product.branch
            location = "in_branch" if branch else "in_warehouse"

            if variants_data:
                # Variant products: one ProductBranchInventory row per variant with qty > 0
                for variant_data in variants_data:
                    variant = ProductVariant.objects.create(
                        product=product, **variant_data
                    )
                    qty = variant.size_qty or 0
                    if qty > 0:
                        ProductBranchInventory.objects.create(
                            companyId=company,
                            product=product,
                            variant=variant,
                            warehouse=warehouse,
                            branch=branch,
                            location=location,
                            quantity=qty,
                        )
            else:
                # Simple product: one ProductBranchInventory row for the whole product
                if initial_stock > 0:
                    ProductBranchInventory.objects.create(
                        companyId=company,
                        product=product,
                        variant=None,
                        warehouse=warehouse,
                        branch=branch,
                        location=location,
                        quantity=initial_stock,
                    )
                    # Signal will auto-update Product.in_stock = initial_stock

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

        # Pop stock fields — stock is managed exclusively via StockSummary.
        # Product.in_stock is auto-recalculated by signal after StockSummary changes.
        new_stock = validated_data.pop("in_stock", None)
        validated_data.pop("available", None)

        # Explicitly assign model fields before saving so FK / decimal updates
        # are not lost through deferred instances or serializer edge cases.
        explicit_fields = (
            "unit_conversion_group",
            "display_unit",
            "selling_unit",
            "selling_unit_conversion_factor",
        )

        with transaction.atomic():
            logger.debug(
                "ProductPostSerializer.update incoming id=%s validated_data_keys=%s",
                getattr(instance, "pk", None),
                sorted(validated_data.keys()),
            )
            for field_name in explicit_fields:
                if field_name in validated_data:
                    setattr(instance, field_name, validated_data.pop(field_name))

            # Existing rows may have NULL labels; avoid crashing on PATCH.
            if newlabel_data is not None:
                if instance.newLabel is None:
                    instance.newLabel = NewLabel.objects.create(**newlabel_data)
                    instance.save(update_fields=["newLabel"])
                else:
                    newlabel_serializer = self.fields["newLabel"]
                    newlabel_serializer.update(instance.newLabel, newlabel_data)

            if salelabel_data is not None:
                if instance.saleLabel is None:
                    instance.saleLabel = SaleLabel.objects.create(**salelabel_data)
                    instance.save(update_fields=["saleLabel"])
                else:
                    salelabel_serializer = self.fields["saleLabel"]
                    salelabel_serializer.update(instance.saleLabel, salelabel_data)

            # Handle variants update (replace all variants + their ProductBranchInventory rows)
            if variants_data is not None and len(variants_data) > 0:
                # Delete existing variants (ProductBranchInventory variant rows cascade-delete via FK)
                instance.variants.all().delete()
                # Also explicitly clear any orphan non-variant rows
                ProductBranchInventory.objects.filter(
                    product=instance, variant=None
                ).delete()

                company = instance.companyId
                warehouse = instance.warehouse
                branch = instance.branch
                location = "in_branch" if branch else "in_warehouse"

                for variant_data in variants_data:
                    variant = ProductVariant.objects.create(
                        product=instance, **variant_data
                    )
                    qty = variant.size_qty or 0
                    if qty > 0:
                        ProductBranchInventory.objects.create(
                            companyId=company,
                            product=instance,
                            variant=variant,
                            warehouse=warehouse,
                            branch=branch,
                            location=location,
                            quantity=qty,
                        )
                # Signal will recalculate Product.in_stock automatically.

            if new_stock is not None and not variants_data:
                # Non-variant product: update the single ProductBranchInventory row (or create one)
                updated_count = ProductBranchInventory.objects.filter(
                    product=instance,
                    variant=None,
                ).update(quantity=new_stock)
                if not updated_count:
                    ProductBranchInventory.objects.create(
                        companyId=instance.companyId,
                        product=instance,
                        variant=None,
                        warehouse=instance.warehouse,
                        branch=instance.branch,
                        location="in_branch" if instance.branch else "in_warehouse",
                        quantity=new_stock,
                    )
                # Signal fires automatically and updates Product.in_stock.

            # Update remaining product catalog fields (no stock fields remain here).
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()

            logger.debug(
                "ProductPostSerializer.update saved id=%s display_unit=%s unit_conversion_group=%s selling_unit=%s in_stock=%s",
                instance.pk,
                getattr(instance, "display_unit_id", None),
                getattr(instance, "unit_conversion_group_id", None),
                getattr(instance, "selling_unit_id", None),
                getattr(instance, "in_stock", None),
            )

        return instance


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


class UnitConversionStepSerializer(serializers.ModelSerializer):
    from_unit_name = serializers.CharField(source="from_unit.name", read_only=True)
    to_unit_name = serializers.CharField(source="to_unit.name", read_only=True)

    class Meta:
        model = UnitConversionStep
        fields = [
            "id",
            "group",
            "from_unit",
            "from_unit_name",
            "to_unit",
            "to_unit_name",
            "factor",
            "level",
        ]


class UnitConversionGroupSerializer(serializers.ModelSerializer):
    base_unit_name = serializers.CharField(source="base_unit.name", read_only=True)
    steps = UnitConversionStepSerializer(many=True, read_only=True)

    class Meta:
        model = UnitConversionGroup
        fields = [
            "id",
            "name",
            "base_unit",
            "base_unit_name",
            "created_at",
            "steps",
        ]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "phone", "email", "address"]


class InventoryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCategory
        fields = ["id", "name", "description", "is_active"]


class InventoryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
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

    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    reason = serializers.CharField(
        max_length=200, required=False, default="Stock addition"
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    reference_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    expiry_date = serializers.DateField(required=False, allow_null=True)
    warranty_expiry_date = serializers.DateField(required=False, allow_null=True)


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


class StockTransferItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name", read_only=True, default=None
    )
    variant_label = serializers.SerializerMethodField()

    class Meta:
        model = StockTransferItem
        fields = [
            "id",
            "transfer",
            "serial_item",
            "product",
            "product_name",
            "variant",
            "variant_label",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_variant_label(self, obj):
        if not obj.variant:
            return None
        parts = [obj.variant.size_name, obj.variant.color]
        return " · ".join(p for p in parts if p) or obj.variant.unique_code


class StockTransferItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransferItem
        fields = ["serial_item", "product", "variant", "notes"]


class StockTransferSerializer(serializers.ModelSerializer):
    items = StockTransferItemSerializer(many=True, read_only=True)
    source_warehouse_name = serializers.CharField(
        source="source_warehouse.name", read_only=True, default=None
    )
    source_branch_name = serializers.CharField(
        source="source_branch.name", read_only=True, default=None
    )
    destination_warehouse_name = serializers.CharField(
        source="destination_warehouse.name", read_only=True, default=None
    )
    destination_branch_name = serializers.CharField(
        source="destination_branch.name", read_only=True, default=None
    )

    class Meta:
        model = StockTransfer
        fields = [
            "id",
            "transfer_number",
            "company",
            "transfer_type",
            "status",
            "source_warehouse",
            "source_warehouse_name",
            "source_branch",
            "source_branch_name",
            "destination_warehouse",
            "destination_warehouse_name",
            "destination_branch",
            "destination_branch_name",
            "notes",
            "transferred_by",
            "completed_at",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = (
            "id",
            "transfer_number",
            "completed_at",
            "created_at",
            "updated_at",
        )


class StockSummaryPOSSerializer(serializers.ModelSerializer):
    """Serializer for POS catalog items backed by a single ProductBranchInventory row.

    Each row represents one product (or one product+variant) at a specific branch.
    The ``id`` field is a cart-safe composite key so the frontend can send it back
    verbatim during order creation.
    """

    # Stable cart id: composite for variant rows, plain product UUID otherwise.
    id = serializers.SerializerMethodField()
    summary_id = serializers.UUIDField(source="id", read_only=True)

    # Product fields
    product_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()
    sku = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    # Stock
    in_stock = serializers.IntegerField(source="quantity", read_only=True)
    available = serializers.SerializerMethodField()

    # Variant fields (null for non-variant products)
    variant_id = serializers.SerializerMethodField()
    variant_size = serializers.SerializerMethodField()
    variant_size_name = serializers.SerializerMethodField()
    variant_color = serializers.SerializerMethodField()
    variant_size_code = serializers.SerializerMethodField()

    # Unit Conversion Group
    unit_conversion_group = serializers.IntegerField(
        source="product.unit_conversion_group_id", read_only=True
    )
    display_unit = serializers.IntegerField(
        source="product.display_unit_id", read_only=True
    )
    display_unit_name = serializers.CharField(
        source="product.display_unit.name", read_only=True
    )
    selling_unit = serializers.IntegerField(
        source="product.selling_unit_id", read_only=True
    )
    selling_unit_name = serializers.CharField(
        source="product.selling_unit.name", read_only=True
    )
    selling_unit_conversion_factor = serializers.IntegerField(
        source="product.selling_unit_conversion_factor", read_only=True
    )

    class Meta:
        model = ProductBranchInventory
        fields = [
            "summary_id",
            "id",
            "product_id",
            "variant_id",
            "name",
            "category",
            "code",
            "sku",
            "price",
            "image",
            "in_stock",
            "available",
            "variant_size",
            "variant_size_name",
            "variant_color",
            "variant_size_code",
            "unit_conversion_group",
            "display_unit",
            "display_unit_name",
            "selling_unit",
            "selling_unit_name",
            "selling_unit_conversion_factor",
        ]

    def get_id(self, obj):
        product_id = str(obj.product_id)
        if obj.variant_id:
            return f"{product_id}__var__{obj.variant_id}"
        return product_id

    def get_product_id(self, obj):
        return str(obj.product_id) if obj.product_id else None

    def get_variant_id(self, obj):
        return str(obj.variant_id) if obj.variant_id else None

    def get_name(self, obj):
        base = getattr(obj.product, "name", "") or ""
        if obj.variant_id:
            parts = [
                getattr(obj.variant, "size_name", None)
                or getattr(obj.variant, "size", None),
                getattr(obj.variant, "color", None),
            ]
            label = " / ".join(p for p in parts if p)
            return f"{base} - {label}" if label else base
        return base

    def get_category(self, obj):
        cat = getattr(obj.product, "category", None)
        return str(cat) if cat else "products"

    def get_code(self, obj):
        if obj.variant_id:
            size_code = getattr(obj.variant, "size_code", None)
            if size_code:
                return size_code
            product_code = getattr(obj.product, "code", None)
            size = getattr(obj.variant, "size", None) or getattr(
                obj.variant, "size_name", None
            )
            if product_code and size:
                return f"{product_code}_{size}"
        return getattr(obj.product, "code", None)

    def get_sku(self, obj):
        return getattr(obj.product, "sku", None)

    def get_price(self, obj):
        if obj.variant_id:
            variant_price = float(getattr(obj.variant, "price", 0) or 0)
            if variant_price > 0:
                return variant_price
        price_sale = float(getattr(obj.product, "priceSale", 0) or 0)
        if price_sale > 0:
            return price_sale
        return float(getattr(obj.product, "price", 0) or 0)

    def get_image(self, obj):
        cover = getattr(obj.product, "coverUrl", None)
        if cover:
            return str(cover) if cover else None
        # ImageField/FileField raises ValueError when no file is associated.
        # Access .name (the stored path string) instead of the descriptor itself.
        image_field = getattr(obj.product, "image", None)
        if not image_field:
            return None
        try:
            return image_field.name or None
        except Exception:
            return None

    def get_available(self, obj):
        return obj.quantity > 0

    def get_variant_size(self, obj):
        return getattr(obj.variant, "size", None) if obj.variant_id else None

    def get_variant_size_name(self, obj):
        return getattr(obj.variant, "size_name", None) if obj.variant_id else None

    def get_variant_color(self, obj):
        return getattr(obj.variant, "color", None) if obj.variant_id else None

    def get_variant_size_code(self, obj):
        return getattr(obj.variant, "size_code", None) if obj.variant_id else None


class StockSummaryInventorySerializer(serializers.Serializer):
    """Inventory Management serializer backed by aggregated StockSummary data."""

    id = serializers.CharField(read_only=True)
    product_id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    category_name = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True, allow_null=True)
    sku = serializers.CharField(read_only=True, allow_null=True)
    unit = serializers.CharField(read_only=True, allow_null=True)
    unit_name = serializers.CharField(read_only=True, allow_null=True)
    current_stock = serializers.FloatField(read_only=True)
    reorder_level = serializers.FloatField(read_only=True)
    max_stock = serializers.FloatField(read_only=True)
    cost_per_unit = serializers.FloatField(read_only=True)
    total_value = serializers.FloatField(read_only=True)
    supplier = serializers.CharField(read_only=True, allow_null=True)
    supplier_name = serializers.CharField(read_only=True, allow_null=True)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    last_updated = serializers.CharField(read_only=True, allow_null=True)
    formatted_last_updated = serializers.CharField(read_only=True, allow_null=True)
    stock_percentage = serializers.FloatField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True)
    location = serializers.CharField(read_only=True, allow_null=True)
    expiry_date = serializers.DateField(read_only=True, allow_null=True)
    warranty_expiry_date = serializers.DateField(read_only=True, allow_null=True)
    notes = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    average_usage = serializers.FloatField(read_only=True, allow_null=True)
    inventoryType = serializers.CharField(read_only=True, allow_null=True)
    low_stock_threshold = serializers.FloatField(read_only=True)
    generic_name = serializers.CharField(read_only=True, allow_null=True)
    brand_name = serializers.CharField(read_only=True, allow_null=True)
    manufacturer = serializers.CharField(
        read_only=True, allow_null=True, allow_blank=True
    )
    size = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    condition = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    secondary_unit = serializers.CharField(read_only=True, allow_null=True)
    secondary_unit_name = serializers.CharField(read_only=True, allow_null=True)
    unit_conversion_factor = serializers.FloatField(read_only=True)
    in_stock_secondary = serializers.FloatField(read_only=True)
    unit_conversion_group = serializers.CharField(read_only=True, allow_null=True)
    unit_conversion_group_name = serializers.CharField(read_only=True, allow_null=True)
    display_unit = serializers.CharField(read_only=True, allow_null=True)
    display_unit_name = serializers.CharField(read_only=True, allow_null=True)
    selling_unit = serializers.CharField(read_only=True, allow_null=True)
    selling_unit_name = serializers.CharField(read_only=True, allow_null=True)
    selling_unit_conversion_factor = serializers.FloatField(read_only=True)
    price = serializers.FloatField(read_only=True)
    priceSale = serializers.FloatField(read_only=True)
    regular_price = serializers.FloatField(read_only=True)
    image = serializers.CharField(read_only=True, allow_null=True)
    quantity = serializers.FloatField(read_only=True)
    variants = serializers.ListField(child=serializers.DictField(), read_only=True)


class StockTransferCreateSerializer(serializers.ModelSerializer):
    """Write serializer: accepts nested items on creation."""

    items = StockTransferItemWriteSerializer(many=True)

    class Meta:
        model = StockTransfer
        fields = [
            "company",
            "transfer_type",
            "source_warehouse",
            "source_branch",
            "destination_warehouse",
            "destination_branch",
            "notes",
            "transferred_by",
            "items",
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        transfer = StockTransfer.objects.create(**validated_data)
        for item_data in items_data:
            StockTransferItem.objects.create(transfer=transfer, **item_data)
        return transfer
