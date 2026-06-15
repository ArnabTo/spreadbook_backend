from django.contrib import admin

from .models import ProformaInvoice, ProformaInvoiceItem


class ProformaInvoiceItemInline(admin.TabularInline):
    model = ProformaInvoiceItem
    extra = 0
    readonly_fields = ("product_total", "amount", "tax_amount", "total")


@admin.register(ProformaInvoice)
class ProformaInvoiceAdmin(admin.ModelAdmin):
    list_display = ("bill_number", "date", "customer", "total", "grand_total")
    search_fields = ("bill_number",)
    inlines = [ProformaInvoiceItemInline]
