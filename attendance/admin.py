from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Attendance, AttendanceData


@admin.register(Attendance)
class AttendanceAdmin(ImportExportModelAdmin):
          list_display = (
          'id',
          'creator',
          'company_id',
          'company',
          'person',
          'is_present',
          'time_in',
          'time_out',
          'count_hrs',
          'createDate',
     )
          
          
@admin.register(AttendanceData)
class AttendanceDataAdmin(ImportExportModelAdmin):
          list_display = (
          'id',
          'attendance_data',
          'status',
          'createDate',
     )