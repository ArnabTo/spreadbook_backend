from django.db import models
from django.utils import timezone


class ReportLog(models.Model):
    """Model to track report generation history"""

    REPORT_TYPES = [
        ("sales_overview", "Sales Overview"),
        ("product_analysis", "Product Analysis"),
        ("staff_performance", "Staff Performance"),
        ("inventory_analysis", "Inventory Analysis"),
        ("financial_analytics", "Financial Analytics"),
        ("customer_analytics", "Customer Analytics"),
    ]

    FORMAT_TYPES = [
        ("json", "JSON"),
        ("csv", "CSV"),
        ("pdf", "PDF"),
    ]

    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    format_type = models.CharField(max_length=10, choices=FORMAT_TYPES, default="json")
    period = models.CharField(max_length=20, default="month")
    start_date = models.DateField()
    end_date = models.DateField()
    generated_at = models.DateTimeField(default=timezone.now)
    generated_by = models.CharField(max_length=100, default="System")
    execution_time = models.FloatField(null=True, blank=True)  # in seconds
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "reports_log"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.period} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"


class ReportSchedule(models.Model):
    """Model to schedule automatic report generation"""

    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
    ]

    name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=50, choices=ReportLog.REPORT_TYPES)
    format_type = models.CharField(
        max_length=10, choices=ReportLog.FORMAT_TYPES, default="pdf"
    )
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    recipients = models.TextField(help_text="Email addresses separated by commas")
    is_active = models.BooleanField(default=True)
    last_generated = models.DateTimeField(null=True, blank=True)
    next_generation = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "reports_schedule"
        ordering = ["next_generation"]

    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"


class ReportTemplate(models.Model):
    """Model to store custom report templates"""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=50, choices=ReportLog.REPORT_TYPES)
    template_config = models.JSONField(
        default=dict, help_text="JSON configuration for report customization"
    )
    is_default = models.BooleanField(default=False)
    created_by = models.CharField(max_length=100, default="System")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reports_template"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ReportMetrics(models.Model):
    """Model to store key metrics for dashboard"""

    metric_name = models.CharField(max_length=100)
    metric_value = models.DecimalField(max_digits=15, decimal_places=2)
    metric_type = models.CharField(max_length=50)  # revenue, orders, profit, etc.
    period_start = models.DateField()
    period_end = models.DateField()
    calculated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "reports_metrics"
        unique_together = ["metric_name", "metric_type", "period_start", "period_end"]
        ordering = ["-calculated_at"]

    def __str__(self):
        return f"{self.metric_name}: {self.metric_value} ({self.period_start} to {self.period_end})"
