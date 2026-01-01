from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Changelog


@admin.register(Changelog)
class ChangelogAdmin(ImportExportModelAdmin):
     list_display=('id',
               'name', 'is_read', 'createdAt'
               
               )
     ordering = ('-id',)