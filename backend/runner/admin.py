from django.contrib import admin
from .models import CheckReport, CheckMetrics, CheckError

class CheckErrorInline(admin.TabularInline):
    model = CheckError
    extra = 0
    readonly_fields = ['timestamp']
    can_delete = False

class CheckMetricsInline(admin.StackedInline):
    model = CheckMetrics
    can_delete = False
    readonly_fields = ['total_checks', 'passed_checks', 'failed_checks', 'success_rate']

@admin.register(CheckReport)
class CheckReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'timestamp', 'status', 'execution_time', 'system_version']
    list_filter = ['status', 'timestamp']
    readonly_fields = ['timestamp']
    inlines = [CheckMetricsInline, CheckErrorInline]
    search_fields = ['status', 'system_version']

@admin.register(CheckError)
class CheckErrorAdmin(admin.ModelAdmin):
    list_display = ['check_name', 'report', 'severity', 'timestamp']
    list_filter = ['severity', 'timestamp']
    search_fields = ['check_name', 'message']
    readonly_fields = ['timestamp']