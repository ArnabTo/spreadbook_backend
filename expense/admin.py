from import_export.admin import ImportExportModelAdmin

from django.contrib import admin
from expense.models import Category, Expense, ExpenseItem


@admin.register(Expense)
class ExpenseAdmin(ImportExportModelAdmin):
     list_display = ('id', 'amount', 'category', 'content', 'createdAt')


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
     list_display = ('name',)

@admin.register(ExpenseItem)
class CategoryAdmin(ImportExportModelAdmin):
     list_display = ('title',)
