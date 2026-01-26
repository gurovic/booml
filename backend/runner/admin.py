from django.contrib import admin

from .models import (
    Report,
    Problem,
    Submission,
    ProblemData,
    Notebook,
    Cell,
    Contest,
    Section,
    Course,
    CourseParticipant,
    PreValidation,
    Leaderboard,
    ProblemDescriptor,
    Tag
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

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "__str__")

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
    list_display = (
        "id",
        "title",
        "course",
        "is_published",
        "approval_status",
        "access_type",
        "is_rated",
        "scoring",
        "registration_type",
        "status",
        "start_time",
        "duration_minutes",
        "created_by",
        "created_at",
    )
    list_filter = ("is_published", "approval_status", "access_type", "is_rated", "scoring", "registration_type", "status", "course")
    search_fields = ("title", "course__title", "created_by__username", "source")
    filter_horizontal = ("problems", "allowed_participants")
    list_editable = ("is_published", "approval_status", "access_type")

    def save_model(self, request, obj, form, change):
        # Auto-approve contests when admin publishes them
        if obj.is_published and obj.approval_status == Contest.ApprovalStatus.PENDING:
            obj.approval_status = Contest.ApprovalStatus.APPROVED
            obj.approved_by = request.user
            from django.utils import timezone
            obj.approved_at = timezone.now()
        super().save_model(request, obj, form, change)


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
    list_display = (
        "id",
        "problem",
        "id_column",
        "target_column",
        "metric_name",
        "has_custom_metric",
        "check_order",
        "created_at",
    )
    search_fields = ("problem__title",)

    def has_custom_metric(self, obj):
        return obj.has_custom_metric()

    has_custom_metric.boolean = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "section", "is_open", "created_at")
    list_filter = ("is_open", "created_at")
    search_fields = ("title", "owner__username")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "parent", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "owner__username")


@admin.register(CourseParticipant)
class CourseParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "user", "role", "is_owner", "added_at")
    list_filter = ("role", "is_owner")
    search_fields = ("course__title", "user__username")

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
