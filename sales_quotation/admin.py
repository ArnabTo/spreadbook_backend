from django.contrib import admin

from .models import Currency, SalesQuotation, SalesQuotationItem


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol", "exchange_rate", "is_active", "companyId")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


class SalesQuotationItemInline(admin.TabularInline):
    model = SalesQuotationItem
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


@admin.register(SalesQuotation)
class SalesQuotationAdmin(admin.ModelAdmin):
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
    search_fields = ("bill_number", "rfq_ref", "subject")
    inlines = [SalesQuotationItemInline]


@admin.register(SalesQuotationItem)
class SalesQuotationItemAdmin(admin.ModelAdmin):
    list_display = ("quotation", "si_no", "product", "unit", "qty", "rate", "total")
