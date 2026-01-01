from decimal import Clamped
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Order, Item, Delivery, History, Timeline, Payment, ShippingAddres
from customers.models import Customer
# from authenticator.models import User as GenUser


class TimelineSerializer(serializers.ModelSerializer):
     class Meta:
          model = Timeline
          # fields = ['id', 'name', 'primary', 'email', 'fullAddress', 'phoneNumber', 'company', 'addressType', ]
          fields = '__all__'
          
     
     
class HistorySerializer(serializers.ModelSerializer):
     timeline = TimelineSerializer(many=True)
     class Meta:
          model = History
          # fields = ['id', 'name', 'primary', 'email', 'fullAddress', 'phoneNumber', 'company', 'addressType', ]
          fields = '__all__'
          
     
     
class ItemSerializer(serializers.ModelSerializer):
     class Meta:
          model = Item
          # fields = ['id', 'name', 'primary', 'email', 'fullAddress', 'phoneNumber', 'company', 'addressType', ]
          fields = '__all__'
          
     
class PaymentSerializer(serializers.ModelSerializer):
     class Meta:
          model = Payment
          # fields = ['id', 'name', 'primary', 'email', 'fullAddress', 'phoneNumber', 'company', 'addressType', ]
          fields = '__all__'
          
     

class ShippingAddresSerializer(serializers.ModelSerializer):
     class Meta:
          model = ShippingAddres
          # fields = ['id', 'name', 'primary', 'email', 'fullAddress', 'phoneNumber', 'company', 'addressType', ]
          fields = '__all__'
          
     
     
     

class DeliverySerializer(serializers.ModelSerializer):
     class Meta:
          model = Delivery
          # fields = ['id', 'name', 'primary', 'email', 'fullAddress', 'phoneNumber', 'company', 'addressType', ]
          fields = '__all__'
          
     
     

class CustomerSerializer(serializers.ModelSerializer):
     class Meta:
          model = Customer
          # fields = ['id', 'name', 'primary', 'email', 'fullAddress', 'phoneNumber', 'company', 'addressType', ]
          fields = '__all__'
          
     
class OrderSerializer(serializers.ModelSerializer):
     customer = CustomerSerializer()
     delivery = DeliverySerializer()
     history  = HistorySerializer()
     items = ItemSerializer(many=True)
     payment = PaymentSerializer()
     shippingAddress = ShippingAddresSerializer()
     class Meta:
          model = Order
          fields = '__all__'





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
#           # instance.taxes_value = validated_data.get("taxes", instance.taxes_value)
#           instance.discount = validated_data.get("discount", instance.discount)
#           instance.subTotal = validated_data.get("subTotal", instance.subTotal)
#           instance.totalAmount = validated_data.get("totalAmount", instance.totalAmount)
#           instance.pdf_file = validated_data.get("pdf_file", instance.pdf_file)
#           instance.due = validated_data.get("due", instance.due)
#           instance.shipping = validated_data.get("shipping", instance.shipping)
#           instance.total = validated_data.get("total", instance.total)
#           instance.user = validated_data.get("user", instance.user)
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
#                          # print(item.get('title', c.title))
#                     else:
#                          continue
#                else:
#                     c = InvoiceItem.objects.create(**item, sell_invoice=instance)
#                     keep_items.append(c.id)
#                     # print("Insider")
          
#           for item in instance.items.all():
#                if item.id not in keep_items:
#                     item.delete()
                    
#           return instance
     
     
