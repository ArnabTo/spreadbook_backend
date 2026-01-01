import json
from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils.html import format_html

from .models import (
                    Performance
                    )

@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
     list_display = ( 'id', 'creator', 'reference', 'createDate', 'amount')
     list_filter = ('company_id',)
     list_per_page = 10
     ordering = ['-createDate']