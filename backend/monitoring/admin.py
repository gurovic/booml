from django.contrib import admin
from .models import SystemMetric


@admin.register(SystemMetric)
class SystemMetricAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'cpu_percent', 'memory_percent', 'disk_percent')
    list_filter = ('timestamp',)
    search_fields = ('timestamp',)
    readonly_fields = ('timestamp', 'cpu_percent', 'memory_percent', 'disk_percent')
    
    def has_add_permission(self, request):
        # Запрещаем добавление записей вручную
        return False

    def has_change_permission(self, request, obj=None):
        # Запрещаем изменение записей
        return False

    def has_delete_permission(self, request, obj=None):
        # Разрешаем удаление записей
        return True