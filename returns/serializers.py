
from django.contrib.auth import get_user_model
from rest_framework import serializers
from company.models import Company
from products.models.product_model import Product
from .models import (
                    Return,
                    ReturnProduct,
                    ReturnProductHistory,
                    ReturnProductCash,
                    ReturnProductItem
                    )
User = get_user_model()


class CreatorDetailsSerializer(serializers.ModelSerializer):
     class Meta:
          model = User
          fields = ['id', 'name', 'email',  'phoneNumber', 'company', 'role', 'payroll']
          # depth = 1
          
          
class ReturnSerializer(serializers.ModelSerializer):
     creator = CreatorDetailsSerializer(required=False)
     class Meta:
          model = Return
          fields = "__all__"
          depth = 1
          
     def create(self, validated_data):
          return_product =  Return.objects.create( 
                                        company_id=self.context['request'].user.company_id,
                                        creator= self.context['request'].user,
                                        company= self.context['request'].user.company,
                                        **validated_data
                                        )
          return return_product
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     
     
class ReturnProductHistorySerialzer(serializers.ModelSerializer):
     # id = serializers.IntegerField(required=False)
     class Meta:
          model = ReturnProductHistory
          fields = '__all__'
          
          # read_only_fields = ('sell_invoice',)
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     

class ReturnProductItemSerialzer(serializers.ModelSerializer):
     id = serializers.IntegerField(required=False)
     class Meta:
          model = ReturnProductItem
          fields = '__all__'
          
          # read_only_fields = ('expense_invoice',)
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     

class ReturnProductPostSerializer(serializers.ModelSerializer):
     # category = CategorySerializer(many=True, required=False)
     items = ReturnProductItemSerialzer(many=True)
     class Meta:
          model = ReturnProduct
          fields = '__all__'
          
          
     # def create(self, validated_data):
     #      return super().create(validated_data)
     
     def create(self, validated_data):
          items_data = validated_data.pop('items')
          
          last_purchase = ReturnProduct.objects.filter(company_id=self.context['request'].user.company_id).order_by('createDate').last()
          
          if last_purchase is None:
               company = Company.objects.get(company_id=self.context['request'].user.company_id)
               last_purchase = 'RTN-1001'
          else:
               last_purchase = last_purchase.returnNumber
               
          returnNumber = last_purchase
          
          purchase_int = int(returnNumber.split('RTN-')[-1])
          width = 4
          new_purchase_int = purchase_int + 1
          formatted = (width - len(str(new_purchase_int))) * "0" + str(new_purchase_int)
          new_purchase_no = 'RTN-' + str(formatted)
          print(new_purchase_no)
          
          validated_data.pop('returnNumber', None)
          purchase_invoice = ReturnProduct.objects.create(
                                                  returnNumber=new_purchase_no, 
                                                  company_id=self.context['request'].user.company_id,
                                                  creator= self.context['request'].user,
                                                  company= self.context['request'].user.company,
                                                  **validated_data
                                                  )
          # sell_invoice = Sale.objects.create(invoiceFrom = 1, invoiceTo="7b014ecd-85c0-4601-a5d0-6283a532240b", **validated_data)
          if purchase_invoice.status  != "draft":
               ReturnProductHistory.objects.create(
                                        company_id=self.context['request'].user.company_id,
                                        creator= self.context['request'].user,
                                        company= self.context['request'].user.company,
                                        reference_id=purchase_invoice.returnNumber,
                                        reference_name=purchase_invoice.status,
                                        source_of_payment= purchase_invoice.payment_method,
                                        paid= purchase_invoice.advance,
                                        total= purchase_invoice.totalAmount,
                                        due=purchase_invoice.due
                                        )
               
          
          for item_data in items_data:
               ReturnProductItem.objects.create(return_invoice=purchase_invoice, **item_data)
               try:
                    product = Product.objects.filter(company_id=self.context['request'].user.company_id).filter(code = item_data['code'])[0]
                    # product = Product.objects.filter(company_id=self.context['request'].user.company_id).get(code = item_data['code'])
                    if purchase_invoice.status == "refund":
                         product.in_stock = product.in_stock + item_data['quantity']
                         product.totalReturns = product.totalReturns + item_data['quantity']
                         product.save()
                    elif purchase_invoice.status == "pending":
                         product.in_stock = product.in_stock + item_data['quantity']                         
                         product.totalReturns = product.totalReturns + item_data['quantity']
                         product.save()
                    elif purchase_invoice.status == "replace":
                         product.in_stock = product.in_stock + item_data['quantity']
                         product.totalReturns = product.totalReturns + item_data['quantity']
                         product.save()
                    else:
                         pass
               except:
                    print("Product does not exist")
          return purchase_invoice
     
     # def update(self, instance, validated_data):
     #      return super().update(instance, validated_data)
     
     def update(self, instance, validated_data):
          items = validated_data.pop('items')
          instance.returnNumber = validated_data.get("returnNumber", instance.returnNumber)
          instance.status = validated_data.get("status", instance.status)
          instance.name = validated_data.get("name", instance.name)
          # instance.expense_type = validated_data.get("expense_type", instance.expense_type)
          instance.due = validated_data.get("due", instance.due)
          instance.amount = validated_data.get("amount", instance.amount)
          instance.category = validated_data.get("category", instance.category)
          instance.subTotal = validated_data.get("subTotal", instance.subTotal)
          instance.totalAmount = validated_data.get("totalAmount", instance.totalAmount)
          instance.content = validated_data.get("content", instance.content)
          instance.dueDate = validated_data.get("dueDate", instance.dueDate)
          instance.payment_method = validated_data.get("payment_method", instance.payment_method)
          instance.totalQty = validated_data.get("totalQty", instance.totalQty)
          instance.advance = validated_data.get("advance", instance.advance)
          # instance.dueDate = validated_data.get("dueDate", instance.dueDate)
          
          instance.save()
          keep_items = []
          # existing_ids = [c.id for c in instance.items]
          for item in items:
               if "id" in item.keys():
                    if ReturnProductItem.objects.filter(id=item["id"]).exists():
                         c = ReturnProductItem.objects.get(id=item["id"])
                         c.title = item.get('title', c.title)
                         c.description = item.get('description', c.description)
                         c.service = item.get('service', c.service)
                         c.quantity = item.get('quantity', c.quantity)
                         c.price = item.get('price', c.price)
                         c.total = item.get('total', c.total)
                         c.code = item.get('code', c.code)
                         c.duration = item.get('duration', c.duration)
                         c.product = item.get('product', c.product)
                         c.return_invoice = item.get('return_invoice', c.return_invoice)
                         # c.product = item.get('product', c.product)
                         c.save()
                         keep_items.append(c.id)
                         # print(item.get('title', c.title))
                    else:
                         continue
               else:
                    c = ReturnProductItem.objects.create(**item, return_invoice=instance)
                    keep_items.append(c.id)
                    # print("Insider")
          
          for item in instance.items.all():
               if item.id not in keep_items:
                    item.delete()
                    
          return instance
     
     
     
class ReturnProductSerializer(serializers.ModelSerializer):
     items = ReturnProductItemSerialzer(many=True)
     class Meta:
          model = ReturnProduct
          fields = '__all__'