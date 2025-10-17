from django.contrib import admin
from .models import Report
from .models import Task

@admin.register(Report)  # Регистрируем модель в админке
class ReportAdmin(admin.ModelAdmin):
    # Какие поля показывать в списке
    list_display = ('file_name', 'metric', 'status', 'submitted_at')
    # Фильтры справа
    list_filter = ('status', 'submitted_at')
    # Поиск по этим полям
    search_fields = ('file_name', 'errors', 'log')
    # Эти поля нельзя редактировать
    readonly_fields = ('submitted_at',)
    # Группировка полей в форме редактирования
    fieldsets = (
        ('Основная информация', {
            'fields': ('file_name', 'metric', 'status')
        }),
        ('Детали проверки', {
            'fields': ('log', 'errors', 'test_data'),
            'classes': ('collapse',)  # Можно свернуть
        }),
        ('Временные метки', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Task)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at")
    search_fields = ("title", "condition")
    list_filter = ("created_at",)
    ordering = ("-created_at",)
