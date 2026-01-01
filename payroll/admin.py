import json

# from num2words import num2words  # Unused import, commenting out

from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils.html import format_html

from .models import (
    # EmployeePayroll,
    SetEmployeePayroll,
    AdditionPayroll,
    OverTimePayroll,
    DeductionPayroll,
    EmployeePaySlip,
)

# @admin.register(EmployeePayroll)
# class EmployeePayrollAdmin(admin.ModelAdmin):
#      list_display = ( 'id', 'employee', 'employeeId', 'company_id', 'basic_salary', 'createDate')
#      list_filter = ('company_id',)
#      list_per_page = 10
#      ordering = ['-createDate']


@admin.register(SetEmployeePayroll)
class SetEmployeePayrollAdmin(admin.ModelAdmin):
    list_display = (
        "id",
     #    "employee_name",
     #    "employee_role",
        "company",
        "salary",
        "payment_type",
        "status",
    )
#     list_filter = ("company_id", "payment_type", "status", "employee__role")
#     list_per_page = 20
#     ordering = ["-id"]
#     search_fields = ("employee__name", "employee__email", "company")
#     raw_id_fields = ("employee", "creator")

#     def employee_name(self, obj):
#         return obj.employee.name if obj.employee else "N/A"

#     employee_name.short_description = "Employee Name"

#     def employee_role(self, obj):
#         return obj.employee.role if obj.employee else "N/A"

#     employee_role.short_description = "Role"


@admin.register(AdditionPayroll)
class AdditionPayrollPayrollAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "company_id", "amount")
    list_filter = ("company_id",)
    list_per_page = 10
    ordering = ["-company_id"]


@admin.register(OverTimePayroll)
class OverTimePayrollAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "company_id", "rate", "amount")
    list_filter = ("company_id",)
    list_per_page = 10
    ordering = ["-company_id"]


@admin.register(DeductionPayroll)
class DeductionPayrollAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "company_id", "rate", "amount")
    list_filter = ("company_id",)
    list_per_page = 10
    ordering = ["-company_id"]


@admin.register(EmployeePaySlip)
class EmployeePaySlipAdmin(admin.ModelAdmin):
    date_hierarchy = "createDate"
    list_display = (
        "id",
        "company_id",
        "status",
        "total_earning",
        "total_deduction",
        "net_total",
        "payroll_month",
    )
    list_filter = ("company_id",)
    list_per_page = 10
    ordering = ["-createDate"]
