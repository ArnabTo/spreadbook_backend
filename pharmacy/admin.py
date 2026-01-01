from django.contrib import admin

from .models import Prescription, PrescriptionItem


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "company", "branch", "customer", "createdAt")
    list_filter = ("status", "company", "branch")
    search_fields = ("id", "doctor_name", "customer__name", "customer__phoneNumber")


@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ("id", "prescription", "product_name", "quantity_prescribed")
    search_fields = ("product_name", "product_sku")
