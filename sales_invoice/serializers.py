import json

from decimal import Decimal

from rest_framework import serializers

from .models import SalesInvoice, SalesInvoiceItem


class SalesInvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    unit_name = serializers.SerializerMethodField()

    class Meta:
        model = SalesInvoiceItem
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


class SalesInvoiceListSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()
    sales_person_name = serializers.SerializerMethodField()
    has_attachment = serializers.SerializerMethodField()
    site_name = serializers.SerializerMethodField()

    class Meta:
        model = SalesInvoice
        fields = [
            "id",
            "bill_number",
            "date",
            "due_date",
            "delivered_on",
            "customer",
            "customer_name",
            "currency",
            "currency_code",
            "sales_person",
            "sales_person_name",
            "po_ref",
            "so_ref",
            "dn_ref_no",
            "inv_type",
            "total",
            "tax_total",
            "discount",
            "product_discount_total",
            "cash_discount_total",
            "paid_amount",
            "pending_amount",
            "grand_total",
            "tax_mode",
            "bill_status",
            "e_invoice_status",
            "site_name",
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

    def get_site_name(self, obj):
        return obj.branch.name if obj.branch else ""


class SalesInvoiceDetailSerializer(serializers.ModelSerializer):
    items = SalesInvoiceItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    sales_person_name = serializers.SerializerMethodField()
    has_attachment = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = SalesInvoice
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
            "due_date",
            "delivered_on",
            "sales_person",
            "sales_person_name",
            "po_ref",
            "so_ref",
            "dn_ref_no",
            "project_ref_no",
            "inv_type",
            "invoice_period",
            "location",
            "attention",
            "payment_terms",
            "narration",
            "enable_seal_and_sign",
            "tax_mode",
            "bill_status",
            "e_invoice_status",
            "bank_account",
            "total",
            "tax_total",
            "discount",
            "product_discount_total",
            "cash_discount_total",
            "paid_amount",
            "pending_amount",
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


class SalesInvoiceItemWriteSerializer(serializers.Serializer):
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


class SalesInvoiceWriteSerializer(serializers.ModelSerializer):
    products = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=True, default=list
    )

    class Meta:
        model = SalesInvoice
        fields = [
            "id",
            "customer",
            "currency",
            "currency_rate",
            "financial_year",
            "date",
            "due_date",
            "delivered_on",
            "sales_person",
            "po_ref",
            "so_ref",
            "dn_ref_no",
            "project_ref_no",
            "inv_type",
            "invoice_period",
            "location",
            "attention",
            "payment_terms",
            "narration",
            "enable_seal_and_sign",
            "tax_mode",
            "bill_status",
            "e_invoice_status",
            "bank_account",
            "total",
            "tax_total",
            "discount",
            "product_discount_total",
            "cash_discount_total",
            "paid_amount",
            "pending_amount",
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
            "po_ref": {"required": False, "allow_blank": True},
            "so_ref": {"required": False, "allow_blank": True},
            "dn_ref_no": {"required": False, "allow_blank": True},
            "project_ref_no": {"required": False, "allow_blank": True},
            "inv_type": {"required": False},
            "invoice_period": {"required": False, "allow_blank": True},
            "location": {"required": False, "allow_blank": True},
            "attention": {"required": False, "allow_blank": True},
            "payment_terms": {"required": False, "allow_blank": True},
            "narration": {"required": False, "allow_blank": True},
            "enable_seal_and_sign": {"required": False},
            "bill_status": {"required": False},
            "e_invoice_status": {"required": False},
            "due_date": {"required": False, "allow_null": True},
            "delivered_on": {"required": False, "allow_null": True},
            "bank_account": {"required": False, "allow_null": True},
            "discount": {"required": False},
            "paid_amount": {"required": False},
            "pending_amount": {"required": False},
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


class SalesInvoiceRegistrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()
    bill_number = serializers.CharField()
    customer_name = serializers.CharField()
    party_invoice_number = serializers.CharField()
    product_name = serializers.CharField()
    unit_name = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=2)
    mrp = serializers.DecimalField(max_digits=18, decimal_places=2)
    cost = serializers.DecimalField(max_digits=18, decimal_places=2)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_cost = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    tax_total = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
