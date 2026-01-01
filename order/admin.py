import json
from decimal import Decimal

from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils.html import format_html
from order.models import Order, Delivery, History, Item, Payment, ShippingAddres, Timeline

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
     list_display = (
          'name',  'status', 'totalQuantity', 'shipping', 'totalAmount',
     )
     

@admin.register(Delivery)
class OrderAdmin(admin.ModelAdmin):
     list_display = (
          'id',
     )
     
@admin.register(History)
class OrderAdmin(admin.ModelAdmin):
     list_display = (
          'id',
     )
     
@admin.register(Item)
class OrderAdmin(admin.ModelAdmin):
     list_display = (
          'id',
     )
     
@admin.register(Payment)
class OrderAdmin(admin.ModelAdmin):
     list_display = (
          'id',
     )

@admin.register(ShippingAddres)
class OrderAdmin(admin.ModelAdmin):
     list_display = (
          'id',
     )

@admin.register(Timeline)
class OrderAdmin(admin.ModelAdmin):
     list_display = (
          'id',
     )
