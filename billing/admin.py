from django.contrib import admin
from .models import Billing, BillingAddress

# Register your models here.
@admin.register(Billing)
class SaleAdmin(admin.ModelAdmin):
     date_hierarchy = 'createDate'
     list_display = (
          'invoiceNumber',
          'creator',
          'company_id',
          'company',
          'amount',
          'account_no',
          'transection_id',
          'createDate',
     )
     list_filter = ('company_id',)
     ordering = ['-createDate']
     list_per_page = 10