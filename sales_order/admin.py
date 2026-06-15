from django.contrib import admin

from .models import SalesOrder, SalesOrderItem


class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
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


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
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
    inlines = [SalesOrderItemInline]


@admin.register(SalesOrderItem)
class SalesOrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "si_no", "product", "unit", "qty", "rate", "total")
