from decimal import Clamped
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Supplier

User = get_user_model()


class SupplierSerializer(serializers.ModelSerializer):
    # Custom field serializations for better frontend integration
    branchId = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    rating = serializers.DecimalField(
        max_digits=3, decimal_places=1, min_value=0, max_value=5, required=False
    )
    phone = serializers.CharField()

    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "supplier_code",
            "address",
            "phone",
            "email",
            "zip_code",
            "country",
            "fax",
            "previous_balance",
            "companyId",
            "branchId",
            "created_at",
            "updated_at",
            # Business fields now part of the model
            "category",
            "contactPerson",
            "paymentTerms",
            "status",
            "rating",
            "totalPurchases",
            "totalSpent",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "totalPurchases")

    def to_representation(self, instance):
        """Customize the output representation"""
        data = super().to_representation(instance)

        # Format phone number to string for frontend
        if instance.phone:
            data["phone"] = str(instance.phone)

        # Format country code to string
        if instance.country:
            data["country"] = str(instance.country)

        # Convert branchId ManyToMany to list of IDs
        if instance.branchId.exists():
            data["branchId"] = [str(branch.id) for branch in instance.branchId.all()]
        else:
            data["branchId"] = []

        # Ensure rating is properly formatted as float
        if instance.rating is not None:
            data["rating"] = float(instance.rating)

        return data

    def create(self, validated_data):
        # Set company info from request user (only if authenticated and has company)
        if "companyId" not in validated_data:
            request = self.context.get("request")
            if request and hasattr(request, "user") and request.user.is_authenticated:
                if hasattr(request.user, "companyId") and request.user.companyId:
                    validated_data["companyId"] = request.user.companyId
                else:
                    # Set to None if user doesn't have company
                    validated_data["companyId"] = None
            else:
                # Set to None for anonymous users
                validated_data["companyId"] = None

        # Create the supplier with all fields
        supplier = Supplier.objects.create(**validated_data)
        return supplier

    def update(self, instance, validated_data):
        # Update all fields including the new business fields
        return super().update(instance, validated_data)

    def validate_rating(self, value):
        """Validate rating is between 0 and 5"""
        if value is not None and (value < 0 or value > 5):
            raise serializers.ValidationError("Rating must be between 0.0 and 5.0")
        return value

    def validate_supplier_code(self, value):
        """Ensure supplier code is unique within the company"""
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            if hasattr(request.user, "company") and request.user.company:
                queryset = Supplier.objects.filter(
                    supplier_code=value, companyId=request.user.company
                )
                # Exclude current instance during updates
                if self.instance:
                    queryset = queryset.exclude(pk=self.instance.pk)

                if queryset.exists():
                    raise serializers.ValidationError(
                        "Supplier code must be unique within your company"
                    )
        else:
            # For anonymous users, check if supplier_code is globally unique
            if value:
                queryset = Supplier.objects.filter(supplier_code=value)
                if self.instance:
                    queryset = queryset.exclude(pk=self.instance.pk)

                if queryset.exists():
                    raise serializers.ValidationError("Supplier code must be unique")
        return value


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
