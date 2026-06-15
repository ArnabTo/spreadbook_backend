import json

from rest_framework import serializers

from .models import DeliveryNote, DeliveryNoteItem


class DeliveryNoteItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    unit_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNoteItem
        fields = [
            "id",
            "product",
            "unit",
            "qty",
            "rate",
            "discount_amount",
            "product_total",
            "amount",
            "tax_percent",
            "tax_amount",
            "total",
            "si_no",
            "product_name",
            "unit_name",
        ]

    def get_product_name(self, obj):
        return getattr(obj.product, "name", "") if obj.product else ""

    def get_unit_name(self, obj):
        return obj.unit.name if obj.unit else ""


class DeliveryNoteListSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()
    sales_person_name = serializers.SerializerMethodField()
    has_attachment = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNote
        fields = [
            "id",
            "bill_number",
            "date",
            "customer",
            "customer_name",
            "currency",
            "currency_code",
            "sales_person",
            "sales_person_name",
            "total",
            "tax_total",
            "product_discount_total",
            "cash_discount_total",
            "grand_total",
            "tax_mode",
            "has_attachment",
            "attachment_name",
            "created_at",
        ]

    def get_customer_name(self, obj):
        return obj.customer.name if obj.customer else ""

    def get_currency_code(self, obj):
        return obj.currency.code if obj.currency else ""

    def get_sales_person_name(self, obj):
        if not obj.sales_person:
            return ""
        return (
            obj.sales_person.fullName
            or obj.sales_person.name
            or obj.sales_person.username
            or ""
        )

    def get_has_attachment(self, obj):
        return bool(obj.attachment)


class DeliveryNoteDetailSerializer(serializers.ModelSerializer):
    items = DeliveryNoteItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    sales_person_name = serializers.SerializerMethodField()
    has_attachment = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNote
        fields = [
            "id",
            "bill_number",
            "customer",
            "customer_name",
            "currency",
            "currency_code",
            "currency_symbol",
            "currency_rate",
            "financial_year",
            "date",
            "sales_person",
            "sales_person_name",
            "site_name",
            "enable_seal_and_sign",
            "po_ref",
            "ref_no",
            "attention",
            "narration",
            "tax_mode",
            "total",
            "tax_total",
            "product_discount_total",
            "cash_discount_total",
            "grand_total",
            "attachment",
            "attachment_url",
            "attachment_name",
            "has_attachment",
            "items",
            "created_at",
            "updated_at",
        ]

    def get_customer_name(self, obj):
        return obj.customer.name if obj.customer else ""

    def get_currency_code(self, obj):
        return obj.currency.code if obj.currency else ""

    def get_currency_symbol(self, obj):
        return obj.currency.symbol if obj.currency else ""

    def get_sales_person_name(self, obj):
        if not obj.sales_person:
            return ""
        return (
            obj.sales_person.fullName
            or obj.sales_person.name
            or obj.sales_person.username
            or ""
        )

    def get_has_attachment(self, obj):
        return bool(obj.attachment)

    def get_attachment_url(self, obj):
        try:
            if obj.attachment and obj.attachment.name:
                return obj.attachment.url
        except Exception:
            return None
        return None


class DeliveryNoteItemWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    product = serializers.IntegerField(required=False, allow_null=True)
    unit = serializers.IntegerField(required=False, allow_null=True)
    qty = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    rate = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)
    discount_amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, default=0
    )
    product_total = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, default=0
    )
    amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, default=0
    )
    tax_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, default=0
    )
    tax_amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, default=0
    )
    total = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, default=0
    )
    si_no = serializers.IntegerField(required=False, default=0)


class DeliveryNoteWriteSerializer(serializers.ModelSerializer):
    """Used for both create and update. Items may be passed as JSON-string or list."""

    products = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=True, default=list
    )

    class Meta:
        model = DeliveryNote
        fields = [
            "id",
            "customer",
            "currency",
            "currency_rate",
            "financial_year",
            "date",
            "sales_person",
            "site_name",
            "enable_seal_and_sign",
            "po_ref",
            "ref_no",
            "attention",
            "narration",
            "tax_mode",
            "total",
            "tax_total",
            "product_discount_total",
            "cash_discount_total",
            "grand_total",
            "attachment",
            "attachment_name",
            "products",
        ]
        extra_kwargs = {
            "currency_rate": {"required": False},
            "attachment": {"required": False, "allow_null": True},
            "attachment_name": {"required": False, "allow_blank": True},
            "financial_year": {"required": False, "allow_null": True},
            "site_name": {"required": False, "allow_blank": True},
            "enable_seal_and_sign": {"required": False},
            "po_ref": {"required": False, "allow_blank": True},
            "ref_no": {"required": False, "allow_blank": True},
            "attention": {"required": False, "allow_blank": True},
            "narration": {"required": False, "allow_blank": True},
        }

    def to_internal_value(self, data):
        try:
            products = data.get("products")
            if isinstance(products, str) and products.strip().startswith("["):
                try:
                    parsed = json.loads(products)
                except (ValueError, TypeError):
                    parsed = None
                if isinstance(parsed, list):
                    data = data.copy() if hasattr(data, "copy") else dict(data)
                    data["products"] = parsed
        except Exception:
            pass
        return super().to_internal_value(data)

    def validate_products(self, value):
        if value in (None, ""):
            return []
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                raise serializers.ValidationError("products must be valid JSON")
        if not isinstance(value, list):
            raise serializers.ValidationError("products must be a list")
        cleaned = []
        for idx, raw in enumerate(value):
            if not isinstance(raw, dict):
                raise serializers.ValidationError(
                    f"products[{idx}] must be an object"
                )
            cleaned.append(raw)
        return cleaned

    def validate(self, attrs):
        if self.instance is not None:
            return attrs
        if not attrs.get("customer"):
            raise serializers.ValidationError({"customer": "Customer is required."})
        if not attrs.get("currency"):
            raise serializers.ValidationError({"currency": "Currency is required."})
        if not attrs.get("date"):
            raise serializers.ValidationError({"date": "Date is required."})
        if not attrs.get("sales_person"):
            raise serializers.ValidationError(
                {"sales_person": "Sales Person is required."}
            )
        return attrs
