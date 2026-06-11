from accounts.models.account_models import Account
from accounts.models.bank_account_model import Bank
from django.contrib import admin


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "name", "parent_name_display", "bank_name", "bank_account_number",
        "email", "opening_balance", "is_debit", "created_at",
    )
    search_fields = ("name", "display_name", "bank_name", "email", "iban_no", "swift_code")
    list_filter = ("parent", "is_debit", "created_at")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Basic Information", {
            "fields": ("parent", "display_name", "name", "mailing_name", "arabic_name"),
        }),
        ("Contact", {
            "fields": ("phone_number", "mobile_number", "email", "description"),
        }),
        ("Banking", {
            "fields": (
                "bank_name", "arabic_bank_name", "bank_account_number",
                "iban_no", "branch_name", "branch_code", "swift_code",
            ),
        }),
        ("Accounting", {
            "fields": ("opening_balance", "is_debit", "cheque_print_enabled"),
        }),
        ("Bilingual Address", {
            "fields": (
                "country_ref", "arabic_country",
                "state_ref", "arabic_state",
                "city", "arabic_city",
                "building_no", "arabic_building_no",
                "street_name", "arabic_street_name",
                "district", "arabic_district",
                "additional_no", "arabic_additional_no",
                "zip_code", "arabic_zip_code",
            ),
        }),
        ("Company", {
            "fields": ("company",),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    def parent_name_display(self, obj):
        return obj.parent.name if obj.parent else "—"
    parent_name_display.short_description = "Parent"
    parent_name_display.admin_order_field = "parent__name"

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ("bank_account_name", "bank_account_number", "account_type", "bank_name", "bank_short_name", "bank_branch")
    search_fields = ("bank_account_name", "bank_account_number")
    list_filter = ("account_type", "bank_name", "bank_short_name", "bank_branch")
    list_per_page = 10
    exclude = ("user",)

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        super().save_model(request, obj, form, change)
