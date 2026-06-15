from django.contrib import admin

from .models import SalesInvoice, SalesInvoiceItem


class SalesInvoiceItemInline(admin.TabularInline):
    model = SalesInvoiceItem
    extra = 0
    fields = (
        "si_no",
        "product",
        "unit",
        "qty",
        "rate",
        "discount_amount",
        "tax_percent",
        "amount",
        "tax_amount",
        "total",
    )


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "bill_number",
        "date",
        "customer",
        "currency",
        "sales_person",
        "grand_total",
        "companyId",
    )
    list_filter = ("date", "tax_mode", "companyId")
    search_fields = ("bill_number", "po_ref", "narration")
    inlines = [SalesInvoiceItemInline]


@admin.register(SalesInvoiceItem)
class SalesInvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "si_no", "product", "unit", "qty", "rate", "total")
