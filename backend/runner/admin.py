from django.contrib import admin

from .models import (
    Report,
    Problem,
    Submission,
    ProblemData,
    Notebook,
    Cell,
    Contest,
    PreValidation,
    Leaderboard,
    ProblemDescriptor,
)

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


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at")
    search_fields = ("title", "statement")
    list_filter = ("created_at",)
    ordering = ("-created_at",)

admin.site.register(Submission)
admin.site.register(ProblemData)


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "owner__username")


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    list_display = ("id", "notebook", "cell_type", "execution_order", "created_at")
    list_filter = ("cell_type",)
    search_fields = ("notebook__title",)


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "_type", "difficulty", "start_time", "status", "open")
    list_filter = ("status", "open")
    search_fields = ("source",)
    filter_horizontal = ("problems",)


@admin.register(PreValidation)
class PreValidationAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "status", "valid", "created_at")
    list_filter = ("status", "valid")
    search_fields = ("submission__user__username", "submission__problem__title")


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(ProblemDescriptor)
class ProblemDescriptorAdmin(admin.ModelAdmin):
    list_display = ("id", "problem", "id_column", "target_column", "check_order", "created_at")
    search_fields = ("problem__title",)
