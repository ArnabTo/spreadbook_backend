from django.contrib import admin
from .models import ReportLog, ReportSchedule, ReportTemplate, ReportMetrics


@admin.register(ReportLog)
class ReportLogAdmin(admin.ModelAdmin):
    list_display = [
        "report_type",
        "format_type",
        "period",
        "generated_at",
        "generated_by",
        "success",
        "execution_time",
    ]
    list_filter = ["report_type", "format_type", "period", "success", "generated_at"]
    search_fields = ["report_type", "generated_by", "error_message"]
    readonly_fields = ["generated_at", "execution_time"]
    date_hierarchy = "generated_at"

    fieldsets = (
        (
            "Report Details",
            {
                "fields": (
                    "report_type",
                    "format_type",
                    "period",
                    "start_date",
                    "end_date",
                )
            },
        ),
        (
            "Generation Info",
            {"fields": ("generated_at", "generated_by", "execution_time", "success")},
        ),
        (
            "Error Details",
            {
                "fields": ("error_message",),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "report_type",
        "frequency",
        "is_active",
        "last_generated",
        "next_generation",
    ]
    list_filter = ["report_type", "frequency", "is_active", "format_type"]
    search_fields = ["name", "recipients"]
    readonly_fields = ["last_generated"]

    fieldsets = (
        (
            "Schedule Details",
            {
                "fields": (
                    "name",
                    "report_type",
                    "format_type",
                    "frequency",
                    "is_active",
                )
            },
        ),
        ("Recipients", {"fields": ("recipients",)}),
        (
            "Status",
            {
                "fields": ("last_generated", "next_generation"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "report_type",
        "is_default",
        "created_by",
        "created_at",
        "updated_at",
    ]
    list_filter = ["report_type", "is_default", "created_at"]
    search_fields = ["name", "description", "created_by"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Template Details",
            {"fields": ("name", "description", "report_type", "is_default")},
        ),
        (
            "Configuration",
            {
                "fields": ("template_config",),
                "description": "JSON configuration for report customization",
            },
        ),
        (
            "Meta Info",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ReportMetrics)
class ReportMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "metric_name",
        "metric_type",
        "metric_value",
        "period_start",
        "period_end",
        "calculated_at",
    ]
    list_filter = ["metric_type", "calculated_at", "period_start"]
    search_fields = ["metric_name", "metric_type"]
    readonly_fields = ["calculated_at"]
    date_hierarchy = "calculated_at"

    fieldsets = (
        ("Metric Details", {"fields": ("metric_name", "metric_type", "metric_value")}),
        ("Period", {"fields": ("period_start", "period_end")}),
        ("Calculation Info", {"fields": ("calculated_at",)}),
    )
