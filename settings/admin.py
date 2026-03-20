from django.contrib import admin
from .models import SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ("company", "branch", "currency", "tax_rate", "updated_at")
    list_filter = ("company", "branch")
    search_fields = ("company__name", "branch__name")
