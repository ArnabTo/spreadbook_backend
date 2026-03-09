from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from products.models.product_model import Product
from rest_framework import serializers
from .models import Sale, InvoiceItem, Refund, RefundItem
from customers.models import Customer
from django.utils import timezone
from django.db import models
import uuid

from common.drf_scoping import (
    get_allowed_branch_ids_for_user,
    get_company_ids_for_user,
    is_unrestricted_user,
)

User = get_user_model()


class QuantizedDecimalField(serializers.DecimalField):
    """A DecimalField that rounds/quantizes incoming values before validation.

    This prevents 400s when clients send floats like 4599.7106 for a 2dp field.
    """

    def to_internal_value(self, data):
        if data is None or data == "":
            # Let DRF handle allow_null/required rules.
            return super().to_internal_value(data)

        try:
            dec = Decimal(str(data))
        except (InvalidOperation, ValueError, TypeError):
            return super().to_internal_value(data)

        quant = Decimal("1").scaleb(-int(self.decimal_places or 0))
        try:
            dec = dec.quantize(quant, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return super().to_internal_value(data)

        # Pass a normalized value back through DecimalField for max_digits checks.
        return super().to_internal_value(str(dec))


def _get_product_for_invoice_item(obj: InvoiceItem | None):
    if not obj:
        return None
    if getattr(obj, "product_id", None):
        return obj.product
    code = getattr(obj, "code", None)
    if not code:
        return None
    try:
        return (
            Product.objects.filter(code=code)
            .only("priceSale", "supplier_price")
            .first()
        )
    except Exception:
        return None


class InvoiceToSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "primary",
            "email",
            "fullAddress",
            "phoneNumber",
            "company",
            "addressType",
        ]


class InvoiceFromSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "primary",
            "email",
            "fullAddress",
            "phoneNumber",
            "company",
            "addressType",
        ]


class InvoiceSerialzer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    priceSale = serializers.SerializerMethodField(read_only=True)
    supplier_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = InvoiceItem
        fields = "__all__"

        read_only_fields = ("sell_invoice",)

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    def get_priceSale(self, obj):
        product = _get_product_for_invoice_item(obj)
        return getattr(product, "priceSale", None) if product else None

    def get_supplier_price(self, obj):
        product = _get_product_for_invoice_item(obj)
        return getattr(product, "supplier_price", None) if product else None


class SaleSerializer(serializers.ModelSerializer):
    items = InvoiceSerialzer(many=True)
    invoiceFrom = InvoiceFromSerializer(required=False)
    invoiceTo = InvoiceToSerializer(required=False)

    class Meta:
        model = Sale
        fields = "__all__"


class SalePostSerializer(serializers.ModelSerializer):
    items = InvoiceSerialzer(many=True)

    # Pharmacy: optional link to an approved prescription
    prescription_id = serializers.UUIDField(
        required=False, allow_null=True, write_only=True
    )

    # invoiceFrom = InvoiceFromSerializer(required=False)
    # invoiceTo = InvoiceToSerializer(required=False)
    class Meta:
        model = Sale
        fields = "__all__"

    # def create(self, validated_data):
    #      return super().create(validated_data)

    def create(self, validated_data):
        prescription_id = validated_data.pop("prescription_id", None)

        items_data = validated_data.pop("items")

        # Feature-flagged enforcement (UI-safe default: off)
        company = validated_data.get("companyId")
        customization = getattr(company, "customization",
                                None) if company else None
        enforce = bool(getattr(customization, "enforce_prescriptions", False))
        enforce_controlled = bool(
            getattr(customization, "enforce_controlled_substances", False)
        )

        if enforce and items_data:
            # Determine if any sold product requires an approved Rx
            required = []
            for item_data in items_data:
                try:
                    product = Product.objects.get(code=item_data["code"])
                except Exception:
                    continue
                if getattr(product, "prescription_required", False) or (
                    enforce_controlled
                    and getattr(product, "controlled_substance", False)
                ):
                    required.append(product)

            if required:
                if not prescription_id:
                    raise serializers.ValidationError(
                        {
                            "prescription_id": "Approved prescription is required for one or more items"
                        }
                    )

                from pharmacy.models import Prescription

                prescription = (
                    Prescription.objects.filter(
                        id=prescription_id, status="approved")
                    .select_related("company", "branch")
                    .first()
                )
                if not prescription:
                    raise serializers.ValidationError(
                        {"prescription_id": "Invalid or not-approved prescription"}
                    )
                if (
                    company is not None
                    and prescription.company_id
                    and str(prescription.company_id)
                    != str(getattr(company, "id", company))
                ):
                    raise serializers.ValidationError(
                        {
                            "prescription_id": "Prescription does not belong to this company"
                        }
                    )

                validated_data["prescription"] = prescription

        last_invoice = Sale.objects.all().order_by("createDate").last()
        if not last_invoice:
            return "INV-0001"
        invoiceNumber = last_invoice.invoiceNumber
        invoice_int = int(invoiceNumber.split("INV-")[-1])
        width = 4
        new_invoice_int = invoice_int + 1
        formatted = (width - len(str(new_invoice_int))) * \
            "0" + str(new_invoice_int)
        new_invoice_no = "INV-" + str(formatted)
        # print(new_invoice_no)
        validated_data.pop("invoiceNumber", None)
        sell_invoice = Sale.objects.create(
            invoiceNumber=new_invoice_no, **validated_data
        )

        # sell_invoice = Sale.objects.create(invoiceFrom = 1, invoiceTo="7b014ecd-85c0-4601-a5d0-6283a532240b", **validated_data)
        for item_data in items_data:
            InvoiceItem.objects.create(sell_invoice=sell_invoice, **item_data)
            product = Product.objects.get(code=item_data["code"])
            print(item_data["quantity"])

            if sell_invoice.status == "paid":
                product.in_stock = product.in_stock - item_data["quantity"]
                product.save()
            elif sell_invoice.status == "overdue":
                product.in_stock = product.in_stock - item_data["quantity"]
                product.save()
            else:
                pass

        return sell_invoice

    def update(self, instance, validated_data):
        items = validated_data.pop("items")
        # instance.invoiceNumber = validated_data.get("invoiceNumber", instance.invoiceNumber)
        instance.status = validated_data.get("status", instance.status)
        instance.payment_method = validated_data.get(
            "payment_method", instance.payment_method
        )
        instance.is_paid = validated_data.get("is_paid", instance.is_paid)
        instance.taxes = validated_data.get("taxes", instance.taxes)
        instance.payment_method = validated_data.get(
            "payment_method", instance.payment_method
        )
        instance.discount = validated_data.get("discount", instance.discount)
        instance.subTotal = validated_data.get("subTotal", instance.subTotal)
        instance.totalQty = validated_data.get("totalQty", instance.totalQty)
        instance.totalAmount = validated_data.get(
            "totalAmount", instance.totalAmount)
        instance.advance = validated_data.get("advance", instance.advance)
        instance.pdf_file = validated_data.get("pdf_file", instance.pdf_file)
        instance.due = validated_data.get("due", instance.due)
        instance.shipping = validated_data.get("shipping", instance.shipping)
        instance.total = validated_data.get("total", instance.total)
        instance.user = validated_data.get("user", instance.user)
        instance.invoiceTo = validated_data.get(
            "invoiceTo", instance.invoiceTo)
        instance.invoiceFrom = validated_data.get(
            "invoiceFrom", instance.invoiceFrom)
        instance.dueDate = validated_data.get("dueDate", instance.dueDate)

        instance.save()
        keep_items = []
        # existing_ids = [c.id for c in instance.items]
        for item in items:
            if "id" in item.keys():
                if InvoiceItem.objects.filter(id=item["id"]).exists():
                    c = InvoiceItem.objects.get(id=item["id"])
                    c.title = item.get("title", c.title)
                    c.description = item.get("description", c.description)
                    c.service = item.get("service", c.service)
                    c.quantity = item.get("quantity", c.quantity)
                    c.price = item.get("price", c.price)
                    c.total = item.get("total", c.total)
                    c.code = item.get("code", c.code)
                    c.duration = item.get("duration", c.duration)
                    c.sell_invoice = item.get("sell_invoice", c.sell_invoice)
                    c.product = item.get("product", c.product)

                    # Signal to chage
                    # if instance.status == "paid":
                    #      product = Product.objects.get(code = item_data['code'])
                    #      product.in_stock = product.in_stock - item_data['quantity']
                    #      product.save()
                    #      print(c)
                    # else:
                    #      print("Updated wihout without paid")
                    # # InvoiceItem.objects.update(id==item["id"],title=c.title)
                    # c.save()
                    keep_items.append(c.id)
                    # print(item.get('title', c.title))
                else:
                    continue
            else:
                c = InvoiceItem.objects.create(**item, sell_invoice=instance)
                keep_items.append(c.id)
                # print("Insider")

        for item in instance.items.all():
            if item.id not in keep_items:
                item.delete()

        return instance


# POS-specific serializers
class POSOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for POS order items"""

    # Backward/forward compatibility: some POS clients send `name` instead of `title`.
    name = serializers.CharField(
        source="title", required=False, allow_blank=True, write_only=True
    )

    # Add properties for new field names
    unit_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, source="price"
    )
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, source="total", read_only=True
    )

    priceSale = serializers.SerializerMethodField(read_only=True)
    supplier_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = InvoiceItem
        fields = [
            "id",
            "menu_item_id",
            "menu_item_code",
            "title",
            "name",
            "description",
            "category",
            "quantity",
            "unit_price",
            "total_price",
            "priceSale",
            "supplier_price",
            "preparation_time",
            "special_instructions",
            "status",
            # Variant fields
            "variant_size",
            "variant_size_name",
            "variant_color",
        ]
        read_only_fields = ["id", "total_price"]

    def get_priceSale(self, obj):
        product = _get_product_for_invoice_item(obj)
        return getattr(product, "priceSale", None) if product else None

    def get_supplier_price(self, obj):
        product = _get_product_for_invoice_item(obj)
        return getattr(product, "supplier_price", None) if product else None

    def validate(self, data):
        """Validate order item data"""
        if data.get("quantity", 0) <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than 0")

        if data.get("price", 0) <= 0:  # Use 'price' field name
            raise serializers.ValidationError(
                "Unit price must be greater than 0")

        return data


class POSOrderSerializer(serializers.ModelSerializer):
    """Serializer for POS orders"""

    items = POSOrderItemSerializer(many=True, write_only=True)
    order_items = POSOrderItemSerializer(
        many=True, read_only=True, source="items")

    # Add properties for new field names
    subtotal = serializers.FloatField(source="subTotal", read_only=True)
    tax_rate = serializers.FloatField(source="taxes")
    tax_amount = serializers.FloatField(source="taxes_value", read_only=True)
    discount_rate = serializers.FloatField(source="discount", default=0)
    total_amount = serializers.FloatField(source="totalAmount", read_only=True)

    service_charge_rate = serializers.FloatField(default=0)
    service_charge_amount = serializers.FloatField(read_only=True)
    tip_amount = serializers.FloatField(default=0)

    served_by = serializers.SerializerMethodField()
    served_by_name = serializers.SerializerMethodField()
    sales_reference_name = serializers.SerializerMethodField()

    company_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    store = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id",
            "order_number",
            "share_token",
            "order_type",
            "table_number",
            "status",
            "payment_method",
            "currency",
            "notes",
            "served_by",
            "served_by_name",
            "sales_reference_name",
            "company_name",
            "branch_name",
            "store",
            "subtotal",
            "tax_rate",
            "tax_amount",
            "discount_rate",
            "discount_amount",
            "service_charge_rate",
            "service_charge_amount",
            "tip_amount",
            "total_amount",
            "is_paid",
            "is_return",
            "kot_printed",
            "order_time",
            "ready_time",
            "served_time",
            "estimated_preparation_time",
            "items",
            "order_items",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "share_token",
            "order_time",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "service_charge_amount",
            "total_amount",
            "estimated_preparation_time",
        ]

    def create(self, validated_data):
        """Create POS order with items"""
        items_data = validated_data.pop("items", [])

        # Create the order
        order = Sale.objects.create(**validated_data)

        # Calculate totals
        subtotal = Decimal("0.00")
        total_prep_time = 0

        # Create order items
        for item_data in items_data:
            # Calculate item total using legacy field names
            item_total = Decimal(
                str(item_data["price"])) * item_data["quantity"]
            item_data["total"] = item_total

            # Create the item
            InvoiceItem.objects.create(sell_invoice=order, **item_data)

            # Update totals
            subtotal += item_total
            total_prep_time = max(
                total_prep_time, item_data.get("preparation_time", 0))

        # Update order totals using legacy field names
        order.subTotal = float(subtotal)

        # Discount amount may be stored explicitly; fall back to percent rate.
        if not order.discount_amount and order.discount:
            order.discount_amount = float(
                subtotal * Decimal(str(order.discount)) / 100)

        base_amount = subtotal - Decimal(str(order.discount_amount or 0))
        if base_amount < 0:
            base_amount = Decimal("0.00")

        order.taxes_value = float(
            base_amount * Decimal(str(order.taxes or 0)) / 100)
        order.service_charge_amount = float(
            base_amount * Decimal(str(order.service_charge_rate or 0)) / 100
        )
        order.totalAmount = float(
            base_amount
            + Decimal(str(order.taxes_value or 0))
            + Decimal(str(order.service_charge_amount or 0))
            + Decimal(str(order.tip_amount or 0))
        )
        order.total = order.totalAmount
        order.totalQty = sum(item["quantity"] for item in items_data)
        order.estimated_preparation_time = total_prep_time

        order.save()

        return order

    def update(self, instance, validated_data):
        """Update POS order"""
        # Remove items from update (they should be updated separately)
        validated_data.pop("items", None)

        # Update order fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update timestamps based on status
        if instance.status == "ready" and not instance.ready_time:
            instance.ready_time = timezone.now()
        elif instance.status == "served" and not instance.served_time:
            instance.served_time = timezone.now()
        elif instance.status == "paid":
            instance.is_paid = True

        instance.save()
        return instance

    def to_representation(self, instance):
        """Customize serialization output"""
        data = super().to_representation(instance)

        # Add computed fields
        data["total_items"] = instance.total_items
        data["display_name"] = instance.display_name
        data["customer_id"] = (
            getattr(instance.customer, "id", None)
            if getattr(instance, "customer", None)
            else None
        )
        data["customer_name"] = (
            getattr(instance.customer, "name", None)
            if getattr(instance, "customer", None)
            else None
        )
        data["customer_phone"] = (
            getattr(instance.customer, "phoneNumber", None)
            if getattr(instance, "customer", None)
            else None
        )
        data["customer_address"] = (
            getattr(instance.customer, "fullAddress", None)
            if getattr(instance, "customer", None)
            else None
        )
        data["status_display"] = instance.get_status_display()
        data["order_type_display"] = instance.get_order_type_display()

        return data

    def get_company_name(self, obj):
        company = getattr(obj, "companyId", None) or getattr(
            getattr(obj, "branch", None), "company", None
        )
        return getattr(company, "name", None) if company else None

    def get_branch_name(self, obj):
        branch = getattr(obj, "branch", None)
        return getattr(branch, "name", None) if branch else None

    def get_store(self, obj):
        """Return store details used in receipt header (nullable fields allowed)."""

        branch = getattr(obj, "branch", None)
        company = getattr(obj, "companyId", None) or getattr(
            branch, "company", None)

        if not branch and not company:
            return None

        # Address priority
        address = None
        if branch:
            address = getattr(branch, "fullAddress", None) or getattr(
                branch, "location", None
            )
        if not address and company:
            address = getattr(company, "fullAddress", None) or getattr(
                company, "address", None
            )

        # Phone priority
        phone = None
        if branch:
            phone = getattr(branch, "phoneNumber", None) or getattr(
                branch, "phone", None
            )
        if not phone and company:
            phone = getattr(company, "phoneNumber", None) or getattr(
                company, "phone", None
            )

        # Branch model doesn't have website; use company.url
        website = getattr(company, "url", None) if company else None

        return {
            "name": (
                getattr(branch, "name", None)
                if branch
                else getattr(company, "name", None)
            ),
            "address": address,
            "phone": phone,
            "website": website,
        }

    def get_served_by(self, obj):
        u = getattr(obj, "served_by", None)
        if not u:
            return None
        name = (
            getattr(u, "fullName", None)
            or getattr(u, "name", None)
            or getattr(u, "username", None)
        )
        return {"id": getattr(u, "id", None), "name": name or "User"}

    def get_served_by_name(self, obj):
        u = getattr(obj, "served_by", None)
        if not u:
            return None
        return (
            getattr(u, "fullName", None)
            or getattr(u, "name", None)
            or getattr(u, "username", None)
        )

    def get_sales_reference_name(self, obj):
        u = getattr(obj, "sales_reference", None)
        if not u:
            return None
        return (
            getattr(u, "fullName", None)
            or getattr(u, "name", None)
            or getattr(u, "username", None)
        )


# Mapping of frontend order types to backend order types
ORDER_TYPE_MAPPING = {
    # Frontend format → Backend format (must match ORDER_TYPE_CHOICE in models.py)
    "In-Store": "In-Store",
    "in-store": "In-Store",
    "Pickup": "Pickup",
    "pickup": "Pickup",
    "Delivery": "Delivery",
    "delivery": "Delivery",
    # Legacy/alternate formats
    "dine-in": "In-Store",
    "takeaway": "Pickup",
}


class POSOrderCreateSerializer(serializers.Serializer):
    """Simplified serializer for creating POS orders from frontend"""

    # Accept both frontend and backend order_type formats
    order_type = serializers.CharField(max_length=20)
    table_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    payment_method = serializers.CharField(max_length=20, default="cash")
    is_paid = serializers.BooleanField(required=False)
    currency = serializers.CharField(max_length=10, default="BDT")
    notes = serializers.CharField(required=False, allow_blank=True)
    special_instructions = serializers.CharField(
        required=False, allow_blank=True
    )  # Order-level notes
    tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=10.0)

    # Optional cashier attribution (employee switch)
    served_by_id = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    # Optional sales reference: staff by whose reference this sale was made
    sales_reference_id = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    # Allow creating orders even if inventory is insufficient.
    # This is intended for inventory mismatch / new items scenarios.
    # Backend still enforces that only privileged roles can enable this.
    allow_out_of_stock = serializers.BooleanField(
        required=False, default=False)

    # Allow POS to provide a manual unit price for Product lines when the server-side
    # Product has no usable price (0 / missing). This is primarily for correcting
    # catalog issues at checkout time.
    allow_price_override = serializers.BooleanField(
        required=False, default=False)

    # Allow cash payments to be partial (remaining amount becomes due).
    # When enabled, backend will not reject cash_received < total and will store
    # the paid portion in `advance` and the remainder in `due`.
    allow_partial_cash = serializers.BooleanField(
        required=False, default=False)

    def validate_order_type(self, value):
        """Normalize order_type from frontend format to backend format"""
        if not value:
            raise serializers.ValidationError("Order type is required")

        normalized = ORDER_TYPE_MAPPING.get(value)
        if normalized is None:
            allowed = list(set(ORDER_TYPE_MAPPING.keys()))
            raise serializers.ValidationError(
                f"Invalid order type '{value}'. Allowed values: {', '.join(sorted(allowed))}"
            )
        return normalized

    # Cash payment tracking fields
    cash_received = QuantizedDecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    change_amount = QuantizedDecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )

    # Cash short waiver (allowed short amount for cash payments)
    cash_waiver = QuantizedDecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )

    # Customer fields (for takeaway/delivery)
    customer_phone = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    customer_name = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    customer_address = serializers.CharField(required=False, allow_blank=True)
    customer_id = serializers.UUIDField(required=False, allow_null=True)

    # Pharmacy: optional link to an approved prescription
    prescription_id = serializers.UUIDField(required=False, allow_null=True)

    # Discount fields
    discount_type = serializers.ChoiceField(
        choices=["none", "percentage", "fixed", "promo"], default="none", required=False
    )
    discount_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0, required=False
    )
    promo_code = serializers.CharField(
        max_length=50, required=False, allow_blank=True)

    # Tip / service charge
    tip_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    service_charge_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )

    # Order items
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        error_messages={"min_length": "At least one item is required"},
    )

    def validate_items(self, items):
        """Validate order items"""
        for item in items:
            # Accept both restaurant payloads (`name`) and older/newer payloads (`title`).
            required_fields = ["id", "quantity"]
            for field in required_fields:
                if field not in item:
                    raise serializers.ValidationError(
                        f"Item missing required field: {field}"
                    )

            # At least one of name/title must be present (or resolvable later from DB).
            # We keep this permissive, but avoid creating DB rows with NULL title.
            name_or_title = (
                item.get("name") or item.get("title") or "").strip()
            if not name_or_title:
                # Don't hard-fail here if the item can be resolved from DB by id/code.
                # Validation happens again during create when MenuItem/Product lookup is available.
                pass

            if item["quantity"] <= 0:
                raise serializers.ValidationError(
                    "Item quantity must be greater than 0"
                )

            # Legacy restaurant payloads always send a price; MegaShop product lines can
            # be priced server-side (but we still accept client price for compatibility).
            if "price" in item and item["price"] <= 0:
                raise serializers.ValidationError(
                    "Item price must be greater than 0")

        return items

    def _validate_cash_fields(self, attrs):

        payment_method = (attrs.get("payment_method") or "").lower()
        cash_received = attrs.get("cash_received")
        change_amount = attrs.get("change_amount")
        cash_waiver = attrs.get("cash_waiver")

        # Normalize waiver
        if cash_waiver is not None and cash_waiver < 0:
            raise serializers.ValidationError(
                {"cash_waiver": "Must be 0 or greater"})

        # Only meaningful for cash payments.
        if payment_method != "cash":
            if cash_waiver not in (None, 0, 0.0):
                raise serializers.ValidationError(
                    {"cash_waiver": "Only allowed for cash payments"}
                )
            return attrs

        # For cash: validate waiver does not exceed configured max.
        from django.conf import settings

        max_waiver = getattr(settings, "POS_CASH_WAIVER_MAX", Decimal("0"))
        try:
            max_waiver = Decimal(str(max_waiver))
        except Exception:
            max_waiver = Decimal("0")

        if cash_waiver is not None and cash_waiver > max_waiver:
            raise serializers.ValidationError(
                {"cash_waiver":
                    f"Must be \u2264 {max_waiver} (POS_CASH_WAIVER_MAX)"}
            )

        # If cash_received is provided, waiver cannot exceed the short amount.
        # Note: order total is computed server-side; frontend-provided totals are not trusted.
        if cash_received is not None:
            # We can't compute the total here (depends on items/promo/tax), so we do a sanity check
            # based on provided change_amount when present.
            if change_amount is not None:
                # If change is negative, it represents short amount (or mismatch)
                if (
                    change_amount < 0
                    and cash_waiver is not None
                    and cash_waiver > (-change_amount)
                ):
                    raise serializers.ValidationError(
                        {"cash_waiver": "Cannot exceed short amount"}
                    )

        return attrs

    def validate_table_number(self, value):
        """Validate table number for dine-in orders"""
        # MegaShop POS does not require table/counter selection.
        # Keep `table_number` purely optional for backward compatibility.
        return value

    def validate(self, attrs):
        """Validate customer and cash-related fields for POS order creation"""
        attrs = super().validate(attrs)

        order_type = attrs.get("order_type")

        # Require customer phone for delivery only (Pickup phone is optional)
        if order_type == "Delivery":
            customer_phone = attrs.get("customer_phone")
            if not customer_phone or not customer_phone.strip():
                raise serializers.ValidationError(
                    {
                        "customer_phone": "Customer phone number is required for delivery orders"
                    }
                )

        # Require address for delivery
        if order_type == "Delivery":
            customer_address = attrs.get("customer_address")
            if not customer_address or not customer_address.strip():
                raise serializers.ValidationError(
                    {
                        "customer_address": "Delivery address is required for delivery orders"
                    }
                )

        return self._validate_cash_fields(attrs)

    def create(self, validated_data):
        """Create POS order from frontend data"""
        from django.db import transaction

        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        if not request_user:
            raise serializers.ValidationError("Missing request user")

        items_data = validated_data.pop("items")

        requested_allow_out_of_stock = bool(
            validated_data.pop("allow_out_of_stock", False)
        )

        allow_price_override = bool(
            validated_data.pop("allow_price_override", False))

        allow_partial_cash = bool(
            validated_data.pop("allow_partial_cash", False))

        prescription_id = validated_data.pop("prescription_id", None)

        served_by_id = validated_data.pop("served_by_id", None)

        sales_reference_id = validated_data.pop("sales_reference_id", None)

        is_paid = bool(validated_data.pop("is_paid", False))

        company = validated_data.pop("companyId", None)
        branch = validated_data.pop("branch", None)

        # Feature-flagged enforcement (UI-safe default: off)
        customization = getattr(company, "customization",
                                None) if company else None
        enforce = bool(getattr(customization, "enforce_prescriptions", False))
        enforce_controlled = bool(
            getattr(customization, "enforce_controlled_substances", False)
        )

        prescription = None
        if enforce and items_data:
            product_ids = set()
            product_codes = set()
            for item_data in items_data:
                pid = (
                    item_data.get("product_id")
                    or item_data.get("productId")
                    or item_data.get("product")
                )
                if pid:
                    product_ids.add(str(pid))

                # Allow supershop-style payloads that identify products by code/SKU.
                # This keeps restaurant menu-item payloads unaffected.
                pcode = (
                    item_data.get("code")
                    or item_data.get("product_code")
                    or item_data.get("productCode")
                )
                if pcode is not None and str(pcode).strip():
                    product_codes.add(str(pcode).strip())

            if product_ids or product_codes:
                products_qs = Product.objects.none()
                if product_ids:
                    q = Product.objects.filter(id__in=list(product_ids))
                    if company is not None:
                        q = q.filter(companyId=company)
                    products_qs = products_qs | q
                if product_codes:
                    q = Product.objects.filter(code__in=list(product_codes))
                    if company is not None:
                        q = q.filter(companyId=company)
                    products_qs = products_qs | q

                products = products_qs.distinct()
                requires_rx = [
                    p
                    for p in products
                    if getattr(p, "prescription_required", False)
                    or (
                        enforce_controlled and getattr(
                            p, "controlled_substance", False)
                    )
                ]

                if requires_rx:
                    if not prescription_id:
                        raise serializers.ValidationError(
                            {
                                "prescription_id": "Approved prescription is required for one or more items"
                            }
                        )

                    from pharmacy.models import Prescription

                    prescription = (
                        Prescription.objects.filter(
                            id=prescription_id,
                            status="approved",
                            company=company,
                        )
                        .select_related("company", "branch")
                        .first()
                    )
                    if not prescription:
                        raise serializers.ValidationError(
                            {"prescription_id": "Invalid or not-approved prescription"}
                        )

        served_by_user = request_user
        if served_by_id is not None:
            served_by_id = str(served_by_id).strip()

        if (
            served_by_id
            and request_user
            and served_by_id != str(getattr(request_user, "id", ""))
        ):
            # Only privileged roles can attribute sales to another employee.
            if not (
                is_unrestricted_user(request_user)
                or getattr(request_user, "role", None)
                in {"super_admin", "admin", "manager"}
            ):
                raise serializers.ValidationError(
                    {"served_by_id": "You do not have permission to switch cashier"}
                )

            served_by_user = User.objects.filter(id=served_by_id).first()
            if not served_by_user:
                raise serializers.ValidationError(
                    {"served_by_id": "Invalid employee"})

            # Company scope check
            if company is not None:
                allowed_company_ids = get_company_ids_for_user(served_by_user)
                company_id = str(getattr(company, "id", company))
                if company_id not in allowed_company_ids:
                    raise serializers.ValidationError(
                        {"served_by_id": "Employee is not in the same company"}
                    )

            # Branch scope check (when branch is fixed)
            if branch is not None and not is_unrestricted_user(served_by_user):
                allowed_branch_ids = get_allowed_branch_ids_for_user(
                    served_by_user)
                if (
                    allowed_branch_ids is not None
                    and str(branch.id) not in allowed_branch_ids
                ):
                    raise serializers.ValidationError(
                        {"served_by_id": "Employee does not have access to this branch"}
                    )

        # Extract customer data
        customer_phone = validated_data.pop("customer_phone", None)
        customer_name = validated_data.pop("customer_name", None)
        customer_address = validated_data.pop("customer_address", None)
        customer_id = validated_data.pop("customer_id", None)

        tip_amount = Decimal(str(validated_data.pop("tip_amount", 0) or 0))
        service_charge_rate = Decimal(
            str(validated_data.pop("service_charge_rate", 0) or 0)
        )

        with transaction.atomic():
            # Only privileged roles can oversell inventory.
            requester_role = getattr(request_user, "role", None)
            allow_out_of_stock = bool(
                requested_allow_out_of_stock
                and (
                    is_unrestricted_user(request_user)
                    or requester_role in {"super_admin", "admin", "manager", "cashier"}
                )
            )

            # Handle customer creation/linking when a phone is provided.
            customer = None
            order_type = validated_data.get("order_type")

            if customer_phone and order_type in [
                "Pickup",
                "Delivery",
                "In-Store",
            ]:
                if customer_id:
                    customer = Customer.objects.filter(
                        id=customer_id,
                        companyId=company,
                    ).first()

                    if customer:
                        customer.lastVisit = timezone.now().date()
                        customer.save(update_fields=["lastVisit"])

                if not customer:
                    # Search by phone number
                    customer = Customer.objects.filter(
                        phoneNumber=customer_phone, companyId=company
                    ).first()

                    if customer:
                        customer.lastVisit = timezone.now().date()
                        customer.save(update_fields=["lastVisit"])

                    if not customer:
                        # Create new customer
                        customer = Customer.objects.create(
                            companyId=company,
                            branch=branch,
                            name=customer_name or "Walk-in Customer",
                            phoneNumber=customer_phone,
                            fullAddress=customer_address or "",
                            category="regular",
                            status="Active",
                        )

            # Get special instructions (order-level notes)
            special_instructions = validated_data.get(
                "special_instructions", "")
            order_notes = validated_data.get("notes", "")

            # Combine notes if both exist
            combined_notes = order_notes
            if special_instructions:
                combined_notes = (
                    f"{combined_notes}\nSpecial Instructions: {special_instructions}"
                    if combined_notes
                    else f"Special Instructions: {special_instructions}"
                )

            # Get cash payment tracking info
            cash_received = validated_data.get("cash_received")
            change_amount = validated_data.get("change_amount")
            cash_waiver = validated_data.get("cash_waiver")

            payment_method = (validated_data.get(
                "payment_method") or "cash").lower()

            # Add cash payment info to notes if applicable
            if cash_received is not None and change_amount is not None:
                cash_info = f"\nCash Received: {cash_received}, Change: {change_amount}"
                combined_notes = (
                    f"{combined_notes}{cash_info}"
                    if combined_notes
                    else cash_info.strip()
                )

            if cash_waiver is not None and cash_waiver > 0:
                waiver_info = f"\nCash Waiver: {cash_waiver}"
                combined_notes = (
                    f"{combined_notes}{waiver_info}"
                    if combined_notes
                    else waiver_info.strip()
                )

            # For legacy compatibility, store cashAmount as received + waiver (effective tendered).
            effective_cash_amount = cash_received
            if effective_cash_amount is not None and cash_waiver is not None:
                effective_cash_amount = effective_cash_amount + cash_waiver

            # Resolve sales_reference user
            sales_reference_user = None
            if sales_reference_id:
                sales_reference_id = str(sales_reference_id).strip()
                if sales_reference_id:
                    sales_reference_user = User.objects.filter(
                        id=sales_reference_id
                    ).first()

            # Create order with legacy field names
            order = Sale.objects.create(
                companyId=company,
                branch=branch,
                customer=customer,  # Link to customer
                invoiceTo=customer,  # Legacy field compatibility
                prescription=prescription,
                order_type=validated_data["order_type"],
                table_number=validated_data.get("table_number"),
                payment_method=validated_data.get("payment_method", "cash"),
                is_paid=is_paid,
                currency=validated_data.get("currency", "BDT"),
                notes=combined_notes,
                # Use legacy field name
                taxes=validated_data.get("tax_rate", 10.0),
                cashAmount=(
                    float(effective_cash_amount)
                    if effective_cash_amount is not None
                    else 0
                ),
                tip_amount=float(tip_amount),
                service_charge_rate=float(service_charge_rate),
                status="confirmed",
                served_by=served_by_user,
                sales_reference=sales_reference_user,
            )

            # Generate order number immediately after creation
            order.generate_order_number()

            # Process items
            subtotal = Decimal("0.00")
            total_prep_time = 0

            # Build a sanitized items list for promo calculations (server-trusted price/id).
            items_for_promo: list[dict] = []

            from menu_items.models import MenuItem

            for item_data in items_data:
                raw_item_id = str(item_data.get("id") or "").strip()
                if not raw_item_id:
                    raise serializers.ValidationError(
                        {"items": "Item id is required"})

                stored_item_id = raw_item_id

                # 1) Try resolving as MenuItem (restaurant mode)
                menu_item = None
                try:
                    uuid.UUID(raw_item_id)
                except Exception:
                    menu_item = None
                else:
                    menu_qs = MenuItem.objects.filter(id=raw_item_id)
                    if company is not None:
                        menu_qs = menu_qs.filter(companyId=company)
                    if branch is not None:
                        menu_qs = menu_qs.filter(branch=branch)
                    menu_item = menu_qs.first()

                # 2) Try resolving as Product (MegaShop mode)
                product = None
                if not menu_item:
                    try:
                        uuid.UUID(raw_item_id)
                    except Exception:
                        product = None
                    else:
                        prod_qs = Product.objects.select_for_update().filter(
                            id=raw_item_id
                        )
                        if company is not None:
                            prod_qs = prod_qs.filter(companyId=company)
                        if branch is not None:
                            prod_qs = prod_qs.filter(
                                models.Q(branch=branch) | models.Q(
                                    branch__isnull=True)
                            )
                        product = prod_qs.first()

                    # Allow product lookup by code/SKU-like field when id isn't a UUID.
                    if not product:
                        pcode = (
                            item_data.get("code")
                            or item_data.get("product_code")
                            or item_data.get("productCode")
                            or item_data.get("item_code")
                        )
                        if pcode is not None and str(pcode).strip():
                            prod_qs = Product.objects.select_for_update().filter(
                                code=str(pcode).strip()
                            )
                            if company is not None:
                                prod_qs = prod_qs.filter(companyId=company)
                            if branch is not None:
                                prod_qs = prod_qs.filter(
                                    models.Q(branch=branch)
                                    | models.Q(branch__isnull=True)
                                )
                            product = prod_qs.first()

                # 3) Fallback: use explicit product_id when the cart id is a composite
                #    key (e.g. "<uuid>__var__<variantKey>") used for variant lines.
                if not product and not menu_item:
                    explicit_product_id = str(
                        item_data.get("product_id") or "").strip()
                    if explicit_product_id and explicit_product_id != raw_item_id:
                        try:
                            uuid.UUID(explicit_product_id)
                        except Exception:
                            pass
                        else:
                            prod_qs = Product.objects.select_for_update().filter(
                                id=explicit_product_id
                            )
                            if company is not None:
                                prod_qs = prod_qs.filter(companyId=company)
                            if branch is not None:
                                prod_qs = prod_qs.filter(
                                    models.Q(branch=branch)
                                    | models.Q(branch__isnull=True)
                                )
                            product = prod_qs.first()
                            if product:
                                stored_item_id = str(product.id)

                # Create order item using legacy field names
                quantity = int(item_data["quantity"])
                title = item_data.get("name") or item_data.get("title")
                category = item_data.get("category", "")
                client_unit_price = Decimal(str(item_data.get("price") or 0))
                unit_price = client_unit_price
                # Whether the POS sold this item in secondary units (e.g. 1 Strip, not 1 Box).
                # Resolved fully inside `if product:` block below once we have the product record.
                _sold_in_sec = False

                # ── Variant fields (extracted early so stock check can use variant qty) ──
                variant_size = (item_data.get("variant_size")
                                or "").strip() or None
                variant_size_name = (
                    item_data.get("variant_size_name") or ""
                ).strip() or None
                variant_color = (item_data.get(
                    "variant_color") or "").strip() or None
                variant_obj = None

                if product:
                    # If the payload used a product code as "id", normalize stored id to UUID.
                    try:
                        uuid.UUID(raw_item_id)
                    except Exception:
                        stored_item_id = str(product.id)

                    # ── Variant detection FIRST ───────────────────────────────────────
                    # Variant products store stock in ProductVariant.size_qty, NOT in
                    # Product.in_stock or ProductBranchInventory.in_stock. We detect this
                    # before calling get_effective_numbers so branch inventory is never
                    # consulted for the stock check of variant products.
                    from products.models import ProductVariant as _PV

                    _product_has_variants = _PV.objects.filter(
                        product=product).exists()

                    if _product_has_variants and (variant_size or variant_size_name or variant_color):
                        # Level 1: exact match
                        vqs = _PV.objects.filter(product=product)
                        if variant_size:
                            vqs = vqs.filter(size=variant_size)
                        if variant_color:
                            vqs = vqs.filter(color=variant_color)
                        variant_obj = vqs.first()

                        # Level 2: case-insensitive fallback (handles "L" vs "l" etc.)
                        if variant_obj is None:
                            vqs2 = _PV.objects.filter(product=product)
                            if variant_size:
                                vqs2 = vqs2.filter(size__iexact=variant_size)
                            if variant_color:
                                vqs2 = vqs2.filter(color__iexact=variant_color)
                            variant_obj = vqs2.first()

                    # ── Pricing (uses effective numbers / branch price) ────────────────
                    from products.branch_inventory import get_effective_numbers

                    numbers = get_effective_numbers(product, branch)
                    effective = (
                        numbers.priceSale if numbers.priceSale > 0 else numbers.price
                    )
                    if not effective or float(effective) <= 0:
                        effective = numbers.regular_price or 0

                    if effective and float(effective) > 0:
                        unit_price = Decimal(str(effective))
                    else:
                        unit_price = Decimal("0")
                        if allow_price_override and client_unit_price > 0:
                            unit_price = client_unit_price

                    title = getattr(product, "name", None) or title
                    category = getattr(product, "category", None) or category

                    # Determine unit mode: secondary (e.g. Strip) vs primary (e.g. Box).
                    _factor = int(
                        getattr(product, "unit_conversion_factor", 0) or 0)
                    _sec_id = getattr(product, "secondary_unit_id", None)
                    _sold_in_sec = (
                        bool(item_data.get("sold_in_secondary_unit"))
                        and _sec_id is not None
                        and _factor > 0
                    )

                    # ── Stock enforcement ─────────────────────────────────────────────
                    # Priority (independent of ProductBranchInventory for variants):
                    #   1. Matched variant   → variant.size_qty          (ProductVariant)
                    #   2. Any variant exists but none matched            (SUM size_qty)
                    #   3. Secondary-unit product                         (in_stock_secondary)
                    #   4. Regular product                                (branch/product in_stock)
                    if variant_obj is not None:
                        current_stock = int(
                            getattr(variant_obj, "size_qty", 0) or 0)
                    elif _product_has_variants:
                        from django.db.models import Sum as _Sum
                        current_stock = int(
                            _PV.objects.filter(product=product)
                            .aggregate(total=_Sum("size_qty"))["total"]
                            or 0
                        )
                    elif _sold_in_sec:
                        current_stock = int(
                            getattr(product, "in_stock_secondary", 0) or 0
                        )
                    else:
                        current_stock = int(numbers.in_stock or 0)
                    if (not allow_out_of_stock) and current_stock < quantity:
                        raise serializers.ValidationError(
                            {
                                "items": f"Insufficient stock for {title}. Available: {current_stock}, requested: {quantity}"
                            }
                        )

                    # Branch stock adjustment: skip for variant products (their stock is
                    # deducted by the _invoice_item_stock_deduct post_save signal) and
                    # secondary-unit products (also handled by signal).
                    if branch is not None and not _sold_in_sec and not _product_has_variants:
                        from products.branch_inventory import adjust_branch_stock

                        adjust_branch_stock(
                            product,
                            branch,
                            delta=-quantity,
                            reason="POS sale",
                            notes=f"POS order {str(getattr(order, 'id', ''))}",
                            updated_by=validated_data.get("user")
                            or getattr(self.context.get("request"), "user", None),
                        )
                    # All other cases (non-branch, secondary-unit, or variant products)
                    # are handled by _invoice_item_stock_deduct in signals.py.

                if menu_item and (unit_price <= 0):
                    # Keep legacy behavior: accept client-sent price for menu items.
                    unit_price = client_unit_price

                # If this is a restaurant MenuItem and client didn't send a name/title,
                # fall back to the MenuItem's display name.
                if menu_item and (not title or not str(title).strip()):
                    title = (
                        getattr(menu_item, "name", None)
                        or getattr(menu_item, "title", None)
                        or title
                    )

                if not title or not str(title).strip():
                    raise serializers.ValidationError(
                        {"items": f"Missing item name/title for item id {raw_item_id}"}
                    )

                if unit_price <= 0:
                    raise serializers.ValidationError(
                        {"items": f"Invalid price for item {title}"}
                    )

                # ── Variant resolution ────────────────────────────────────────────
                # (variant_size/name/color and variant_obj already resolved above,
                #  before the stock check, so no further extraction needed here.)

                item = InvoiceItem.objects.create(
                    sell_invoice=order,
                    menu_item_id=stored_item_id,
                    menu_item_code=item_data.get("item_code", "")
                    or item_data.get("code", "")
                    or "",
                    product=product,
                    title=title,
                    category=category,
                    quantity=quantity,
                    price=unit_price,
                    total=unit_price * quantity,
                    preparation_time=item_data.get("preparation_time", 15),
                    special_instructions=item_data.get(
                        "notes", ""
                    ),  # Save per-item notes
                    sold_in_secondary_unit=_sold_in_sec,
                    # Variant tracking
                    variant=variant_obj,
                    variant_size=variant_size,
                    variant_size_name=variant_size_name,
                    variant_color=variant_color,
                )

                subtotal += item.total
                total_prep_time = max(total_prep_time, item.preparation_time)

                # Promo engine expects a simple list of dicts with id/price/quantity/category.
                items_for_promo.append(
                    {
                        "id": str(
                            item.menu_item_id
                            or (product.id if product else stored_item_id)
                        ),
                        "name": title,
                        "category": category or "",
                        "price": float(unit_price),
                        "quantity": quantity,
                    }
                )

            # Calculate and update order totals using legacy field names
            discount_type = validated_data.get("discount_type", "none")
            discount_value = Decimal(
                str(validated_data.get("discount_value", 0)))
            promo_code = validated_data.get("promo_code", "")

            # Calculate discount amount
            discount_amount = Decimal("0.00")
            if discount_type == "percentage":
                discount_amount = subtotal * (discount_value / 100)
            elif discount_type == "fixed":
                discount_amount = min(discount_value, subtotal)
            elif discount_type == "promo" and promo_code:
                # Validate promo code against actual Promotion model
                try:
                    from promotions_discounts.models import Promotion

                    promotion = Promotion.objects.get(
                        code=promo_code.upper(),
                        company=(
                            company
                            or getattr(request_user, "company", None)
                            or getattr(request_user, "companyId", None)
                        ),
                        status="active",
                    )

                    # Check if promotion is valid and can be applied
                    if promotion.can_apply_to_order(float(subtotal)):
                        discount_amount = promotion.calculate_discount_for_cart(
                            float(subtotal), items=items_for_promo
                        )

                        # Increment usage count
                        promotion.used_count += 1
                        promotion.save()

                        # Create usage record for analytics
                        from promotions_discounts.models import PromotionUsage

                        PromotionUsage.objects.create(
                            promotion=promotion,
                            order=order,
                            discount_amount=discount_amount,
                            order_value=float(subtotal),
                            customer=None,  # POS orders don't have customer
                        )
                    else:
                        # Promotion exists but can't be applied (min order value, expired, etc.)
                        discount_amount = Decimal("0.00")

                except Promotion.DoesNotExist:
                    # Invalid promo code - no discount applied
                    discount_amount = Decimal("0.00")
                except Exception as e:
                    # Log error but don't fail the order
                    print(f"Error applying promo code: {e}")
                    discount_amount = Decimal("0.00")

            # Apply discount to subtotal
            after_discount = subtotal - discount_amount

            # Service charge is computed on the discounted base amount
            service_charge_amount = after_discount * \
                (service_charge_rate / 100)

            # Calculate tax on discounted amount
            tax_decimal = Decimal(str(order.taxes)) / 100
            tax_amount = after_discount * tax_decimal

            order.subTotal = float(subtotal)
            order.discount = (
                float(discount_value) if discount_type == "percentage" else 0
            )  # Store percentage rate
            order.discount_amount = float(
                discount_amount
            )  # Store actual discount amount
            order.taxes_value = float(tax_amount)
            order.service_charge_amount = float(service_charge_amount)
            order.tip_amount = float(tip_amount)
            order.totalAmount = float(
                after_discount + tax_amount + service_charge_amount + tip_amount
            )
            order.total = order.totalAmount
            order.totalQty = sum(item_data["quantity"]
                                 for item_data in items_data)
            order.estimated_preparation_time = total_prep_time

            # Add promo code to notes if applicable
            if promo_code:
                existing_notes = order.notes or ""
                order.notes = f"{existing_notes} | Promo: {promo_code}".strip()

            # Cash payment handling:
            # - If allow_partial_cash: accept cash_received < total and store remainder as due.
            # - Otherwise: if marked paid, require cash_received + waiver >= total.
            if payment_method == "cash":
                received_total = Decimal(str(cash_received or 0)) + Decimal(
                    str(cash_waiver or 0)
                )
                order_total = Decimal(str(order.totalAmount or 0))

                # Waiver should never be used if already fully paid by cash received.
                if (
                    cash_waiver
                    and cash_waiver > 0
                    and Decimal(str(cash_received or 0)) >= order_total
                ):
                    raise serializers.ValidationError(
                        {
                            "cash_waiver": "Waiver not allowed when cash received already covers total"
                        }
                    )

                if received_total < order_total:
                    if allow_partial_cash:
                        # Partial payment: force unpaid.
                        order.is_paid = False
                    else:
                        if is_paid:
                            raise serializers.ValidationError(
                                {
                                    "cash_received": "Insufficient cash received (after waiver) for this order total"
                                }
                            )
                        # Prevent bypass by sending is_paid=false with a partial cash amount.
                        if cash_received is not None:
                            raise serializers.ValidationError(
                                {
                                    "cash_received": "Partial cash payment is not enabled for POS"
                                }
                            )
                else:
                    # Fully covered by cash (after waiver)
                    if allow_partial_cash:
                        order.is_paid = True

                # Track cash payments as advance (amount applied) and due (remaining balance).
                # Note: cashAmount already stores tendered cash (received + waiver) for legacy reporting.
                if cash_received is not None:
                    try:
                        applied = min(
                            max(received_total, Decimal("0")),
                            max(order_total, Decimal("0")),
                        )
                        due = max(order_total - applied, Decimal("0"))
                        order.advance = float(applied)
                        order.due = float(due)
                    except Exception:
                        pass

            order.save()

            # Update customer statistics and award loyalty points (100 BDT = 1 point)
            if customer:
                points_earned = customer.update_total_spent(
                    Decimal(str(order.totalAmount))
                )
                # Add points info to order notes
                if points_earned > 0:
                    existing_notes = order.notes or ""
                    order.notes = f"{existing_notes} | Earned {points_earned} loyalty points (100৳ = 1pt)".strip(
                    )
                    order.save(update_fields=["notes"])

        return order


class RefundItemLineInputSerializer(serializers.Serializer):
    # InvoiceItem uses Django's default AutoField (integer PK).
    invoice_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class RefundCreateSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=RefundItemLineInputSerializer(), required=False, allow_empty=True
    )
    reason = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.CharField(required=False, allow_blank=True)
    restock_to_inventory = serializers.BooleanField(
        required=False, default=True)


class RefundItemSerializer(serializers.ModelSerializer):
    invoice_item = serializers.SerializerMethodField()

    class Meta:
        model = RefundItem
        fields = ["id", "invoice_item", "quantity", "unit_price", "total"]

    def get_invoice_item(self, obj):
        item = obj.invoice_item
        return {
            "id": str(item.id),
            "title": item.title,
            "quantity": int(item.quantity or 0),
            "unit_price": float(item.unit_price or 0),
            "total_price": float(item.total_price or 0),
        }


class RefundSerializer(serializers.ModelSerializer):
    items = RefundItemSerializer(many=True, read_only=True)

    class Meta:
        model = Refund
        fields = [
            "id",
            "sale",
            "payment_method",
            "reason",
            "total_amount",
            "created_at",
            "items",
        ]
        read_only_fields = ["id", "total_amount", "created_at", "items"]


class RefundListSerializer(serializers.ModelSerializer):
    sale_order_number = serializers.CharField(
        source="sale.order_number", read_only=True
    )
    sale_invoice_number = serializers.CharField(
        source="sale.invoiceNumber", read_only=True
    )
    sale_id = serializers.CharField(source="sale.id", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = [
            "id",
            "sale_id",
            "sale_order_number",
            "sale_invoice_number",
            "payment_method",
            "reason",
            "total_amount",
            "created_at",
            "created_by_name",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        u = obj.created_by
        if not u:
            return None
        return getattr(u, "name", None) or getattr(u, "username", None) or str(u.id)
