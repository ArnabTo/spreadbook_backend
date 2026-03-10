from django.contrib import admin
from .models import SupplierLedger, SupplierPayment


class SupplierPaymentInline(admin.TabularInline):
    model = SupplierPayment
    extra = 0
    fields = ["payment_date", "amount",
              "payment_method", "reference", "is_cancelled"]
    readonly_fields = ["created_at"]


@admin.register(SupplierLedger)
class SupplierLedgerAdmin(admin.ModelAdmin):
    list_display = [
        "po_number", "supplier", "company", "branch",
        "debit_amount", "credit_amount", "balance", "created_at",
    ]
    list_filter = ["company", "branch", "supplier"]
    search_fields = ["po_number", "supplier__name"]
    inlines = [SupplierPaymentInline]
    readonly_fields = ["credit_amount", "balance", "created_at", "updated_at"]


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = [
        "ledger", "amount", "payment_method", "payment_date", "is_cancelled", "created_at",
    ]
    list_filter = ["payment_method", "is_cancelled"]
    search_fields = ["ledger__po_number", "reference"]
