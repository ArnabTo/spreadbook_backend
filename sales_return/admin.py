from django.contrib import admin

from .models import SalesReturn, SalesReturnItem, SalesReturnPayment


class SalesReturnItemInline(admin.TabularInline):
    model = SalesReturnItem
    extra = 1


class SalesReturnPaymentInline(admin.TabularInline):
    model = SalesReturnPayment
    extra = 1


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    list_display = ["bill_number", "date", "customer", "grand_total"]
    inlines = [SalesReturnItemInline, SalesReturnPaymentInline]
