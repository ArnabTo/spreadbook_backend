from decimal import Clamped
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from products.models.product_model import Product
from company.models import Company
from rest_framework import serializers
from .models import( WarrentyProductList,
                    RepairCash,
                    Repair,
                    EnquiryItems,
                    TestDetail,
                    RepairDetail,
                    TrialPeriod,
                    RepairHistory
                    )

from customers.models import Customer
User = get_user_model()

class WarrentyProductListSerialzer(serializers.ModelSerializer):
     # id = serializers.IntegerField(required=False)
     class Meta:
          model = WarrentyProductList
          fields = '__all__'
          
          # read_only_fields = ('sell_invoice',)
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     
     
class InvoiceToSerializer(serializers.ModelSerializer):
     class Meta:
          model = Customer
          fields = ['id', 'name', 'primary', 'email', 'fullAddress', 'phoneNumber', 'company', 'addressType', 'customer_company' ]
          
     
class InvoiceFromSerializer(serializers.ModelSerializer):
     class Meta:
          model = User
          fields = ['id', 'name', 'primary', 'email', 'fullAddress', 'phoneNumber', 'company', 'addressType', 'role' ]

class RepairCashSerialzer(serializers.ModelSerializer):
     # id = serializers.IntegerField(required=False)
     class Meta:
          model = RepairCash
          fields = '__all__'
          
          # read_only_fields = ('sell_invoice',)
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     
     
class RepairHistorySerialzer(serializers.ModelSerializer):
     # id = serializers.IntegerField(required=False)
     class Meta:
          model = RepairHistory
          fields = '__all__'
          
          # read_only_fields = ('sell_invoice',)
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)


class EnquiryItemsSerialzer(serializers.ModelSerializer):
     id = serializers.IntegerField(required=False)
     class Meta:
          model = EnquiryItems
          fields = '__all__'
          
          read_only_fields = ('repair_invoice',)
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     

class RepairSerializer(serializers.ModelSerializer):
     items = EnquiryItemsSerialzer(many=True)
     invoiceFrom = InvoiceFromSerializer(required=False)
     invoiceTo = InvoiceToSerializer(required=False)
     class Meta:
          model = Repair
          fields = '__all__'
          


class RepairPostSerializer(serializers.ModelSerializer):
     items = EnquiryItemsSerialzer(many=True)
     # invoiceFrom = InvoiceFromSerializer(required=False)
     # invoiceTo = InvoiceToSerializer(required=False)
     class Meta:
          model = Repair
          fields = '__all__'
          
     # def create(self, validated_data):
     #      return super().create(validated_data)
     
     def create(self, validated_data):
          
          items_data = validated_data.pop('items')
          
          last_invoice = Repair.objects.filter(company_id=self.context['request'].user.company_id).order_by('createDate').last()
          
          if last_invoice is None:
               company = Company.objects.get(company_id=self.context['request'].user.company_id)
               last_invoice = company.invoiceNumber
          else:
               last_invoice = last_invoice.invoiceNumber 
               
          invoiceNumber = last_invoice  
          # print("Invoice")
          invoice_int = int(invoiceNumber.split('MR-')[-1])
          width = 4
          new_invoice_int = invoice_int + 1
          formatted = (width - len(str(new_invoice_int))) * "0" + str(new_invoice_int)
          new_invoice_no = 'MR-' + str(formatted)
          # print(last_invoice)
          validated_data.pop('invoiceNumber', None)
          
          sell_invoice = Repair.objects.create(invoiceNumber=new_invoice_no, 
                                             company_id=self.context['request'].user.company_id,
                                             creator= self.context['request'].user,
                                             company= self.context['request'].user.company,
                                             **validated_data
                                             )
          
          if sell_invoice.status  != "draft":
               RepairHistory.objects.create(
                                        company_id=self.context['request'].user.company_id,
                                        creator= self.context['request'].user,
                                        company= self.context['request'].user.company,
                                        reference_id=sell_invoice.invoiceNumber,
                                        reference_name=sell_invoice.status,
                                        paid= sell_invoice.advance,
                                        total= sell_invoice.totalAmount,
                                        due=sell_invoice.due
                                        )
               
          # sell_invoice = Sale.objects.create(invoiceFrom = 1, invoiceTo="7b014ecd-85c0-4601-a5d0-6283a532240b", **validated_data)
          for item_data in items_data:
               EnquiryItems.objects.create(repair_invoice=sell_invoice, **item_data)
          return sell_invoice
     
     
     def update(self, instance, validated_data):
          items = validated_data.pop('items')
          # instance.invoiceNumber = validated_data.get("invoiceNumber", instance.invoiceNumber)
          
          instance.status = validated_data.get("status", instance.status)
          instance.payment_method = validated_data.get("payment_method", instance.payment_method)
          instance.is_paid = validated_data.get("is_paid", instance.is_paid)
          instance.taxes = validated_data.get("taxes", instance.taxes)
          instance.payment_method = validated_data.get("payment_method", instance.payment_method)
          instance.change = validated_data.get("change", instance.change)
          instance. commission = validated_data.get("commission", instance.commission)
          instance.discount = validated_data.get("discount", instance.discount)
          instance.subTotal = validated_data.get("subTotal", instance.subTotal)
          instance.totalQty = validated_data.get("totalQty", instance.totalQty)
          instance.totalAmount = validated_data.get("totalAmount", instance.totalAmount)
          instance.advance = validated_data.get("advance", instance.advance)
          instance.pdf_file = validated_data.get("pdf_file", instance.pdf_file)
          instance.due = validated_data.get("due", instance.due)
          instance.shipping = validated_data.get("shipping", instance.shipping)
          instance.total = validated_data.get("total", instance.total)
          instance.user = validated_data.get("user", instance.user)
          instance.invoiceTo = validated_data.get("invoiceTo", instance.invoiceTo)
          instance.invoiceFrom = validated_data.get("invoiceFrom", instance.invoiceFrom)
          instance.dueDate = validated_data.get("dueDate", instance.dueDate)
          
          instance.save()
          keep_items = []
          # existing_ids = [c.id for c in instance.items]
          for item in items:
               if "id" in item.keys():
                    if EnquiryItems.objects.filter(id=item["id"]).exists():
                         c = EnquiryItems.objects.get(id=item["id"])
                         c.title = item.get('title', c.title)
                         c.description = item.get('description', c.description)
                         c.serial = item.get('serial', c.serial)
                         c.service = item.get('service', c.service)
                         c.quantity = item.get('quantity', c.quantity)
                         c.discount = item.get('discount', c.discount)
                         c.price = item.get('price', c.price)
                         c.total = item.get('total', c.total)
                         c.code = item.get('code', c.code)
                         c.duration = item.get('duration', c.duration)
                         c.sell_invoice = item.get('sell_invoice', c.sell_invoice)
                         keep_items.append(c.id)
                         # print(item.get('title', c.title))
                    else:
                         continue
               else:
                    c = EnquiryItems.objects.create(**item, repair_invoice=instance)
                    keep_items.append(c.id)
                    # print("Insider")
          
          for item in instance.items.all():
               if item.id not in keep_items:
                    item.delete()
                    
          return instance
     
     