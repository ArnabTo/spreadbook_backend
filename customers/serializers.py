from decimal import Clamped
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Customer

User = get_user_model()


class CustomerSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for Customer model with business logic
    """

    # Custom field serializations for better frontend integration
    loyaltyPoints = serializers.IntegerField(read_only=True)
    totalOrders = serializers.IntegerField(read_only=True)
    totalSpent = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    lastVisit = serializers.DateField(read_only=True)
    phone = serializers.CharField(source="phoneNumber", required=False)
    address = serializers.CharField(source="fullAddress", required=False)

    class Meta:
        model = Customer
        fields = [
            "id",
            "companyId",
            "branch",
            "name",
            "customer_code",
            "email",
            "phone",
            "phoneNumber",
            "category",
            "status",
            "totalOrders",
            "totalSpent",
            "loyaltyPoints",
            "lastVisit",
            "address",
            "fullAddress",
            "addressType",
            "city",
            "zip_code",
            "gender",
            "company",
            "url",
            "balance",
            "previous_balance",
            "notes",
            "avatarUrl",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "companyId",
            "customer_code",
            "created_at",
            "updated_at",
            "totalOrders",
            "totalSpent",
            "loyaltyPoints",
            "lastVisit",
        )

    def to_representation(self, instance):
        """Customize the output representation"""
        data = super().to_representation(instance)

        # Format phone number to string for frontend
        if instance.phoneNumber:
            data["phone"] = str(instance.phoneNumber)
        else:
            data["phone"] = ""

        # Ensure address is properly formatted
        if instance.fullAddress:
            data["address"] = str(instance.fullAddress)
        else:
            data["address"] = ""

        # Format decimal fields
        if instance.totalSpent is not None:
            data["totalSpent"] = float(instance.totalSpent)

        if instance.balance is not None:
            data["balance"] = float(instance.balance)

        # Format dates for frontend
        if instance.lastVisit:
            data["lastVisit"] = instance.lastVisit.strftime("%Y-%m-%d")

        return data

    def create(self, validated_data):
        """Create customer with proper initialization"""
        # Handle phone field mapping
        if "phone" in validated_data:
            validated_data["phoneNumber"] = validated_data.pop("phone")

        # Handle address field mapping
        if "address" in validated_data:
            validated_data["fullAddress"] = validated_data.pop("address")

        # Initialize business fields if not provided
        if "totalOrders" not in validated_data:
            validated_data["totalOrders"] = 0
        if "totalSpent" not in validated_data:
            validated_data["totalSpent"] = 0
        if "loyaltyPoints" not in validated_data:
            validated_data["loyaltyPoints"] = 0

        # Create the customer
        customer = Customer.objects.create(**validated_data)
        return customer

    def update(self, instance, validated_data):
        """Update customer with validation"""
        # Handle field mapping
        if "phone" in validated_data:
            validated_data["phoneNumber"] = validated_data.pop("phone")

        if "address" in validated_data:
            validated_data["fullAddress"] = validated_data.pop("address")

        # Don't allow updating read-only business fields directly
        validated_data.pop("totalOrders", None)
        validated_data.pop("totalSpent", None)
        validated_data.pop("loyaltyPoints", None)

        return super().update(instance, validated_data)

    def validate_email(self, value):
        """Validate email uniqueness if provided"""
        if value:
            queryset = Customer.objects.filter(email=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    "A customer with this email already exists."
                )
        return value

    def validate_phone(self, value):
        """Validate phone number uniqueness if provided"""
        if value:
            queryset = Customer.objects.filter(phoneNumber=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    "A customer with this phone number already exists."
                )
        return value

    def validate(self, data):
        """Cross-field validation"""
        # Get name and email from either direct field or mapped field
        name = data.get("name")
        email = data.get("email")

        # Ensure at least name or email is provided
        if not name and not email:
            raise serializers.ValidationError(
                "Customer must have either name or email address."
            )

        return data


# class InvoiceSerialzer(serializers.ModelSerializer):
#      id = serializers.IntegerField(required=False)
#      class Meta:
#           model = InvoiceItem
#           fields = '__all__'

#           read_only_fields = ('sell_invoice',)

#      def create(self, validated_data):
#           return super().create(validated_data)

#      def update(self, instance, validated_data):
#           return super().update(instance, validated_data)


# class SaleSerializer(serializers.ModelSerializer):
#      items = InvoiceSerialzer(many=True)
#      invoiceFrom = InvoiceFromSerializer(required=False)
#      invoiceTo = InvoiceToSerializer(required=False)
#      class Meta:
#           model = Sale
#           fields = '__all__'

# def create(self, validated_data):
#      return super().create(validated_data)

# def create(self, validated_data):

#      items_data = validated_data.pop('items')
#      sell_invoice = Sale.objects.create(**validated_data)
#      # sell_invoice = Sale.objects.create(invoiceFrom = 1, invoiceTo="7b014ecd-85c0-4601-a5d0-6283a532240b", **validated_data)
#      for item_data in items_data:
#           InvoiceItem.objects.create(sell_invoice=sell_invoice, **item_data)
#      return sell_invoice

# def update(self, instance, validated_data):
#      items = validated_data.pop('items')
#      instance.invoiceNumber = validated_data.get("invoiceNumber", instance.invoiceNumber)
#      instance.status = validated_data.get("status", instance.status)
#      instance.payment_method = validated_data.get("payment_method", instance.payment_method)
#      instance.is_paid = validated_data.get("is_paid", instance.is_paid)
#      instance.taxes = validated_data.get("taxes", instance.taxes)
#      instance.discount = validated_data.get("discount", instance.discount)
#      instance.totalAmount = validated_data.get("totalAmount", instance.totalAmount)
#      instance.pdf_file = validated_data.get("pdf_file", instance.pdf_file)
#      instance.due = validated_data.get("due", instance.due)
#      instance.shipping = validated_data.get("shipping", instance.shipping)
#      instance.total = validated_data.get("total", instance.total)
#      instance.user = validated_data.get("user", instance.user)
#      instance.product = validated_data.get("product", instance.product)
#      instance.invoiceTo = validated_data.get("invoiceTo", instance.invoiceTo)
#      instance.invoiceFrom = validated_data.get("invoiceFrom", instance.invoiceFrom)

#      instance.save()
#      keep_items = []
#      # existing_ids = [c.id for c in instance.items]
#      for item in items:
#           if "id" in item.keys():
#                if InvoiceItem.objects.filter(id=item["id"]).exists():
#                     c = InvoiceItem.objects.get(id=item["id"])
#                     c.title = item.get('title', c.title)
#                     c.description = item.get('description', c.description)
#                     c.service = item.get('service', c.service)
#                     c.quantity = item.get('quantity', c.quantity)
#                     c.price = item.get('price', c.price)
#                     c.total = item.get('total', c.total)
#                     c.code = item.get('code', c.code)
#                     c.duration = item.get('duration', c.duration)
#                     c.sell_invoice = item.get('sell_invoice', c.sell_invoice)
#                     c.product = item.get('product', c.product)
#                     # InvoiceItem.objects.update(id==item["id"],title=c.title)
#                     c.save()
#                     keep_items.append(c.id)
#                     print(item.get('title', c.title))
#                else:
#                     continue
#           else:
#                c = InvoiceItem.objects.create(**item, sell_invoice=instance)
#                keep_items.append(c.id)
#                print("Insider")

#      for item in instance.items.all():
#           if item.id not in keep_items:
#                item.delete()

#      return instance


# class SalePostSerializer(serializers.ModelSerializer):
#      items = InvoiceSerialzer(many=True)
#      # invoiceFrom = InvoiceFromSerializer(required=False)
#      # invoiceTo = InvoiceToSerializer(required=False)
#      class Meta:
#           model = Sale
#           fields = '__all__'

#      # def create(self, validated_data):
#      #      return super().create(validated_data)

#      def create(self, validated_data):

#           items_data = validated_data.pop('items')
#           sell_invoice = Sale.objects.create(**validated_data)
#           # sell_invoice = Sale.objects.create(invoiceFrom = 1, invoiceTo="7b014ecd-85c0-4601-a5d0-6283a532240b", **validated_data)
#           for item_data in items_data:
#                InvoiceItem.objects.create(sell_invoice=sell_invoice, **item_data)
#           return sell_invoice

#      def update(self, instance, validated_data):
#           items = validated_data.pop('items')
#           instance.invoiceNumber = validated_data.get("invoiceNumber", instance.invoiceNumber)
#           instance.status = validated_data.get("status", instance.status)
#           instance.payment_method = validated_data.get("payment_method", instance.payment_method)
#           instance.is_paid = validated_data.get("is_paid", instance.is_paid)
#           instance.taxes = validated_data.get("taxes", instance.taxes)
#           instance.discount = validated_data.get("discount", instance.discount)
#           instance.totalAmount = validated_data.get("totalAmount", instance.totalAmount)
#           instance.pdf_file = validated_data.get("pdf_file", instance.pdf_file)
#           instance.due = validated_data.get("due", instance.due)
#           instance.shipping = validated_data.get("shipping", instance.shipping)
#           instance.total = validated_data.get("total", instance.total)
#           instance.user = validated_data.get("user", instance.user)
#           instance.product = validated_data.get("product", instance.product)
#           instance.invoiceTo = validated_data.get("invoiceTo", instance.invoiceTo)
#           instance.invoiceFrom = validated_data.get("invoiceFrom", instance.invoiceFrom)

#           instance.save()
#           keep_items = []
#           # existing_ids = [c.id for c in instance.items]
#           for item in items:
#                if "id" in item.keys():
#                     if InvoiceItem.objects.filter(id=item["id"]).exists():
#                          c = InvoiceItem.objects.get(id=item["id"])
#                          c.title = item.get('title', c.title)
#                          c.description = item.get('description', c.description)
#                          c.service = item.get('service', c.service)
#                          c.quantity = item.get('quantity', c.quantity)
#                          c.price = item.get('price', c.price)
#                          c.total = item.get('total', c.total)
#                          c.code = item.get('code', c.code)
#                          c.duration = item.get('duration', c.duration)
#                          c.sell_invoice = item.get('sell_invoice', c.sell_invoice)
#                          c.product = item.get('product', c.product)
#                          # InvoiceItem.objects.update(id==item["id"],title=c.title)
#                          c.save()
#                          keep_items.append(c.id)
#                          print(item.get('title', c.title))
#                     else:
#                          continue
#                else:
#                     c = InvoiceItem.objects.create(**item, sell_invoice=instance)
#                     keep_items.append(c.id)
#                     print("Insider")

#           for item in instance.items.all():
#                if item.id not in keep_items:
#                     item.delete()

#           return instance
