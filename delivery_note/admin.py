from django.contrib import admin

from .models import DeliveryNote, DeliveryNoteItem


class DeliveryNoteItemInline(admin.TabularInline):
    model = DeliveryNoteItem
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


@admin.register(DeliveryNote)
class DeliveryNoteAdmin(admin.ModelAdmin):
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
    inlines = [DeliveryNoteItemInline]


@admin.register(DeliveryNoteItem)
class DeliveryNoteItemAdmin(admin.ModelAdmin):
    list_display = ("delivery_note", "si_no", "product", "unit", "qty", "rate", "total")
