from django.contrib import admin
from .models import InventoryLog


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "category",
        "log_type",
        "amount",
        "quantity",
        "branch",
        "created_at",
    ]
    list_filter = ["category", "log_type", "created_at"]
    search_fields = ["reference", "description"]
    readonly_fields = ["id", "created_at"]
