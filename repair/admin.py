import json
from decimal import Decimal

from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils.html import format_html
from .models import( WarrentyProductList,
                    RepairCash,
                    Repair,
                    EnquiryItems,
                    TestDetail,
                    RepairDetail,
                    TrialPeriod
                    )

@admin.register(WarrentyProductList)
class WarrentyProductListAdmin(admin.ModelAdmin):
     list_display = (
          'id', 'company_id', 'invoiceNumber', 'code', 'serial', 'repair_count','createDate'
     )
     ordering = ('-createDate',)
     

@admin.register(Repair)
class RepairAdmin(admin.ModelAdmin):
     list_display = (
          'creator', 'company_id', 'company',
          '_invoice_number', 'invoiceFrom', 'invoiceTo',
          'payment_method', 'status', 'is_paid', 'cashAmount', 'change',
          'due', 'total', 'invoiceNumber'
     )
     # actions = ('discount_30',)
     ordering = ('-createDate',)
     list_filter = ('status', 'payment_method', 'invoiceFrom', 'invoiceTo', )
     # exclude = ('user')

     def discount_30(self, request, queryset):
          from math import ceil
          discount = 30  # percentage

          for sale in queryset:
               ''' Set a discount of 30% to selected sales '''
               multiplier = discount / 100
               old_price = sale.total
               discounted_price = ceil(old_price - (old_price * Decimal(multiplier)))
               sale.total = discounted_price
               sale.save(update_fields=['total'])
     discount_30.short_description = 'Set 30%% discount'

     def _status(self, obj):
          '''
          Return the status of the sale colorized in red or green depending on the status.
          '''
          return format_html('<span style="color:green">✅Paid</span>') if obj.is_paid else format_html('<span style="color:red">⌛Due</span>')

     def _invoice_number(self, obj):
          '''
          Return the invoice_number colorized in admin.
          '''
          return format_html('<span style="color:green;">#{}</span>', obj.invoiceNumber)

     def save_model(self, request, obj, form, change):
          '''
          Associate model with current user while saving.
          '''
          obj.user = request.user
          super().save_model(request, obj, form, change)


@admin.register(EnquiryItems)
class EnquiryItemsAdmin(admin.ModelAdmin):
     list_display = (
          'id', 'repair_invoice', 'quantity', 'price', 'code', 'serial','total', 'conditionChoice','enquiryDate'
     )
     ordering = ('-createDate',)
     
     
@admin.register(RepairCash)
class RepairCashAdmin(admin.ModelAdmin):
     list_display = (
          'id', 'creator', 'company_id', 'company', 'amount', 'updateAt', 
     )
     ordering = ('-createDate',)
