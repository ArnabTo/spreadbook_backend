import datetime

from rest_framework import serializers

from .models import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequisition,
    PurchaseRequisitionItem,
    QuickPurchase,
)


class SafeDateField(serializers.DateField):
    """DRF DateField that tolerates datetime values by converting to date."""

    def to_representation(self, value):
        if isinstance(value, datetime.datetime):
            value = value.date()
        return super().to_representation(value)


# Purchase Requisition Serializers
class PurchaseRequisitionItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    inventory_item_name = serializers.CharField(
        source="inventory_item.name", read_only=True
    )

    class Meta:
        model = PurchaseRequisitionItem
        fields = [
            "uuid",
            "product",
            "product_name",
            "product_code",
            "inventory_item",
            "inventory_item_name",
            "item_name",
            "quantity",
            "unit",
            "current_stock",
            "required_stock",
            "notes",
        ]
        read_only_fields = ["uuid"]


class PurchaseRequisitionSerializer(serializers.ModelSerializer):
    items = PurchaseRequisitionItemSerializer(many=True)
    request_date = SafeDateField(required=False)
    required_date = SafeDateField(required=False, allow_null=True)
    approved_date = SafeDateField(required=False, allow_null=True)
    # Backward-compatible field names used by older frontend code.
    createDate = serializers.DateTimeField(source="created_at", read_only=True)
    updateDate = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = PurchaseRequisition
        fields = [
            "uuid",
            "pr_number",
            "requested_by",
            "department",
            "purchase_type",
            "status",
            "request_date",
            "required_date",
            "priority",
            "notes",
            "approved_by",
            "approved_date",
            "items",
            "createDate",
            "updateDate",
        ]
        read_only_fields = ["uuid", "pr_number", "createDate", "updateDate"]
        extra_kwargs = {
            "department": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        requisition = PurchaseRequisition.objects.create(**validated_data)

        for item_data in items_data:
            PurchaseRequisitionItem.objects.create(requisition=requisition, **item_data)

        return requisition

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        # Update requisition fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update items if provided
        if items_data is not None:
            # Delete existing items and create new ones (simpler approach)
            instance.items.all().delete()
            for item_data in items_data:
                PurchaseRequisitionItem.objects.create(
                    requisition=instance, **item_data
                )

        return instance


# Purchase Order Serializers
class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(
        source="inventory_item.name", read_only=True
    )
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    product_unique_code = serializers.CharField(
        source="product.unique_code", read_only=True
    )
    variant_info = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "uuid",
            "inventory_item",
            "inventory_item_name",
            "product",
            "product_name",
            "product_code",
            "product_unique_code",
            "variant",
            "variant_info",
            "name",
            "variant_size",
            "variant_color",
            "variant_unique_code",
            "quantity",
            "unit",
            "unit_price",
            "total_price",
            "expiry_date",
            "warranty_expiry_date",
            "item_status",
            "remarks",
        ]
        read_only_fields = [
            "uuid",
            "total_price",
            "product_name",
            "product_code",
            "product_unique_code",
            "variant_info",
        ]

    def get_variant_info(self, obj):
        if obj.variant:
            return {
                "id": str(obj.variant.id),
                "size": obj.variant.size,
                "color": obj.variant.color,
                "size_code": obj.variant.size_code,
                "unique_code": obj.variant.unique_code,
                "price": obj.variant.price,
                "supplier_price": obj.variant.supplier_price,
            }
        return None


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    company_name = serializers.CharField(source="companyId.name", read_only=True)
    requisition_number = serializers.CharField(
        source="requisition.pr_number", read_only=True
    )
    items_count = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "uuid",
            "po_number",
            "supplier",
            "supplier_name",
            "branch",
            "branch_name",
            "warehouse",
            "warehouse_name",
            "companyId",
            "company_name",
            "requisition",
            "requisition_number",
            "status",
            "order_date",
            "expected_delivery_date",
            "total_amount",
            "notes",
            "created_by",
            "payment_status",
            "items",
            "items_count",
            "total_quantity",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uuid",
            "po_number",
            "total_amount",
            "created_at",
            "updated_at",
            "items_count",
            "total_quantity",
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_total_quantity(self, obj):
        from decimal import Decimal

        total = Decimal("0")
        for it in obj.items.all():
            total += it.quantity or Decimal("0")
        return total

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        po = PurchaseOrder.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=po, **item_data)
        po.recalc_total()
        return po

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
            instance.recalc_total()

        return instance


class QuickPurchaseSerializer(serializers.ModelSerializer):
    sale_id = serializers.UUIDField(source="sale.id", read_only=True)
    invoice_item_id = serializers.IntegerField(source="invoice_item.id", read_only=True)
    product_id = serializers.UUIDField(source="product.id", read_only=True)

    class Meta:
        model = QuickPurchase
        fields = [
            "uuid",
            "companyId",
            "branch",
            "sale_id",
            "invoice_item_id",
            "product_id",
            "name",
            "category",
            "code",
            "sku",
            "unit_cost",
            "unit_price",
            "qty_purchased",
            "qty_sold",
            "remaining_qty",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uuid",
            "sale_id",
            "invoice_item_id",
            "product_id",
            "created_at",
            "updated_at",
        ]


class QuickPurchaseConvertSerializer(serializers.Serializer):
    """Convert remaining qty into a Product row."""

    name = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sku = serializers.CharField(required=False, allow_blank=True, allow_null=True)
