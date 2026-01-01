from rest_framework import serializers
from damage.models import (Damage,
                         DamageProduct,
                         DamageItem,
                         DamageCash,
                         DamageHistory
                         )
from company.models import Company
from products.models.product_model import Product


     
     
class DamageHistorySerialzer(serializers.ModelSerializer):
     # id = serializers.IntegerField(required=False)
     class Meta:
          model = DamageHistory
          fields = '__all__'
          
          # read_only_fields = ('sell_invoice',)
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     
     
     
class DamageItemSerialzer(serializers.ModelSerializer):
     id = serializers.IntegerField(required=False)
     class Meta:
          model = DamageItem
          fields = '__all__'
          
          # read_only_fields = ('expense_invoice',)
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     
     



class DamageProductPostSerializer(serializers.ModelSerializer):
     # category = CategorySerializer(many=True, required=False)
     items = DamageItemSerialzer(many=True)
     class Meta:
          model = DamageProduct
          fields = '__all__'
          
          
     # def create(self, validated_data):
     #      return super().create(validated_data)
     
     def create(self, validated_data):
          items_data = validated_data.pop('items')
          
          last_purchase = DamageProduct.objects.filter(company_id=self.context['request'].user.company_id).order_by('createDate').last()
          
          if last_purchase is None:
               company = Company.objects.get(company_id=self.context['request'].user.company_id)
               last_purchase = 'DMG-1001'
          else:
               last_purchase = last_purchase.damageNumber
               
          damageNumber = last_purchase
          
          purchase_int = int(damageNumber.split('DMG-')[-1])
          width = 4
          new_purchase_int = purchase_int + 1
          formatted = (width - len(str(new_purchase_int))) * "0" + str(new_purchase_int)
          new_purchase_no = 'DMG-' + str(formatted)
          print(new_purchase_no)
          
          validated_data.pop('damageNumber', None)
          purchase_invoice = DamageProduct.objects.create(
                                                  damageNumber=new_purchase_no, 
                                                  company_id=self.context['request'].user.company_id,
                                                  creator= self.context['request'].user,
                                                  company= self.context['request'].user.company,
                                                  **validated_data
                                                  )
          # sell_invoice = Sale.objects.create(invoiceFrom = 1, invoiceTo="7b014ecd-85c0-4601-a5d0-6283a532240b", **validated_data)
          if purchase_invoice.status  != "draft":
               DamageHistory.objects.create(
                                        company_id=self.context['request'].user.company_id,
                                        creator= self.context['request'].user,
                                        company= self.context['request'].user.company,
                                        reference_id=purchase_invoice.damageNumber,
                                        reference_name=purchase_invoice.status,
                                        source_of_payment= purchase_invoice.payment_method,
                                        paid= purchase_invoice.advance,
                                        total= purchase_invoice.totalAmount,
                                        due=purchase_invoice.due
                                        )
               
          
          for item_data in items_data:
               DamageItem.objects.create(damage_invoice=purchase_invoice, **item_data)
               try:
                    product = Product.objects.filter(company_id=self.context['request'].user.company_id).filter(code = item_data['code'])[0]
                    # product = Product.objects.filter(company_id=self.context['request'].user.company_id).get(code = item_data['code'])
                    if purchase_invoice.status == "paid":
                         product.in_stock = product.in_stock - item_data['quantity']
                         product.totalDamages = product.totalDamages + item_data['quantity']
                         product.save()
                    elif purchase_invoice.status == "overdue":
                         product.in_stock = product.in_stock - item_data['quantity']
                         product.totalDamages = product.totalDamages + item_data['quantity']
                         product.save()
                    elif purchase_invoice.status == "pending":
                         product.in_stock = product.in_stock + item_data['quantity']
                         product.totalDamages = product.totalDamages + item_data['quantity']
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
          instance.damageNumber = validated_data.get("damageNumber", instance.damageNumber)
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
                    if DamageItem.objects.filter(id=item["id"]).exists():
                         c = DamageItem.objects.get(id=item["id"])
                         c.title = item.get('title', c.title)
                         c.description = item.get('description', c.description)
                         c.service = item.get('service', c.service)
                         c.quantity = item.get('quantity', c.quantity)
                         c.price = item.get('price', c.price)
                         c.total = item.get('total', c.total)
                         c.code = item.get('code', c.code)
                         c.duration = item.get('duration', c.duration)
                         c.product = item.get('product', c.product)
                         c.damage_invoice = item.get('damage_invoice', c.damage_invoice)
                         # c.product = item.get('product', c.product)
                         c.save()
                         keep_items.append(c.id)
                         # print(item.get('title', c.title))
                    else:
                         continue
               else:
                    c = DamageItem.objects.create(**item, damage_invoice=instance)
                    keep_items.append(c.id)
                    # print("Insider")
          
          for item in instance.items.all():
               if item.id not in keep_items:
                    item.delete()
                    
          return instance
     
     
     
class DamageProductSerializer(serializers.ModelSerializer):
     items = DamageItemSerialzer(many=True)
     class Meta:
          model = DamageProduct
          fields = '__all__'
