from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Report,
    Problem,
    Submission,
    ProblemData,
    Notebook,
    Cell,
    CellRun,
    Contest,
    Section,
    Course,
    CourseParticipant,
    FavoriteCourse,
    PreValidation,
    Leaderboard,
    ProblemDescriptor,
    Tag,
    ContestProblem,
    SiteUpdate,
    Profile,
    TeacherAccessRequest,
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
    list_display = ("id", "title", "owner", "compute_device", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "owner__username")


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    list_display = ("id", "notebook", "cell_type", "execution_order", "created_at")
    list_filter = ("cell_type",)
    search_fields = ("notebook__title",)


@admin.register(CellRun)
class CellRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cell_link",
        "notebook_link",
        "user",
        "status_badge",
        "started_at",
        "duration_display",
    )
    list_filter = ("status", "started_at", "notebook")
    search_fields = ("cell__id", "notebook__title", "user__username", "run_id")
    readonly_fields = ("cell", "notebook", "user", "status", "run_id", "started_at", "finished_at", "duration_display")
    ordering = ("-started_at",)
    date_hierarchy = "started_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def cell_link(self, obj):
        url = f"/admin/runner/cell/{obj.cell_id}/change/"
        return format_html('<a href="{}">Ячейка #{}</a>', url, obj.cell_id)

    cell_link.short_description = "Ячейка"

    def notebook_link(self, obj):
        url = f"/admin/runner/notebook/{obj.notebook_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.notebook)

    notebook_link.short_description = "Блокнот"

    def status_badge(self, obj):
        colors = {
            CellRun.STATUS_RUNNING: "#f0ad4e",
            CellRun.STATUS_FINISHED: "#5cb85c",
            CellRun.STATUS_ERROR: "#d9534f",
        }
        labels = {
            CellRun.STATUS_RUNNING: "Выполняется",
            CellRun.STATUS_FINISHED: "Завершено",
            CellRun.STATUS_ERROR: "Ошибка",
        }
        color = colors.get(obj.status, "#999")
        label = labels.get(obj.status, obj.status)
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px">{}</span>',
            color,
            label,
        )

    status_badge.short_description = "Статус"

    def duration_display(self, obj):
        seconds = obj.duration_seconds
        if seconds is None:
            return "—"
        if seconds < 60:
            return f"{seconds:.1f} с"
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes} мин {secs:.0f} с"

    duration_display.short_description = "Длительность"


class ContestProblemInline(admin.TabularInline):
    model = ContestProblem
    extra = 0
    autocomplete_fields = ("problem",)
    ordering = ("position", "id")
    fields = ("problem", "position")


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
        "allow_upsolving",
        "created_by",
        "created_at",
    )
    list_filter = (
        "is_published",
        "approval_status",
        "access_type",
        "is_rated",
        "scoring",
        "registration_type",
        "status",
        "allow_upsolving",
        "course",
    )
    search_fields = ("title", "course__title", "created_by__username", "source")
    inlines = (ContestProblemInline,)
    filter_horizontal = ("allowed_participants",)
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
        "score_curve_p",
        "score_reference_metric",
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

@admin.register(FavoriteCourse)
class FavoriteCourseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "position", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "course__title")
    ordering = ("user_id", "position", "id")

@admin.register(SiteUpdate)
class SiteUpdateAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_published", "created_at")
    list_filter = ("is_published", "created_at")
    search_fields = ("title", "body")
    ordering = ("-created_at",)
    
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "gpu_access")
    list_filter = ("role", "gpu_access")
    search_fields = ("user__username", "user__email")


@admin.register(TeacherAccessRequest)
class TeacherAccessRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at", "reviewed_by", "reviewed_at")
    list_filter = ("status", "created_at", "reviewed_at")
    search_fields = ("user__username", "user__email", "comment", "review_comment")
    readonly_fields = ("created_at", "updated_at", "reviewed_at", "proof_link")
    actions = ("approve_requests", "reject_requests")

    fieldsets = (
        ("Заявка", {
            "fields": ("user", "status", "proof", "proof_link", "comment")
        }),
        ("Модерация", {
            "fields": ("review_comment", "reviewed_by", "reviewed_at")
        }),
        ("Служебное", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def proof_link(self, obj):
        if not obj or not obj.proof:
            return "Нет файла"
        return format_html('<a href="{}" target="_blank" rel="noopener">Открыть подтверждение</a>', obj.proof.url)

    proof_link.short_description = "Файл подтверждения"

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = TeacherAccessRequest.objects.filter(pk=obj.pk).values_list("status", flat=True).first()

        super().save_model(request, obj, form, change)

        if obj.status == TeacherAccessRequest.STATUS_APPROVED and old_status != TeacherAccessRequest.STATUS_APPROVED:
            obj.approve(reviewer=request.user, comment=obj.review_comment)
        elif obj.status == TeacherAccessRequest.STATUS_REJECTED and old_status != TeacherAccessRequest.STATUS_REJECTED:
            obj.reject(reviewer=request.user, comment=obj.review_comment)

    @admin.action(description="Одобрить выбранные заявки")
    def approve_requests(self, request, queryset):
        for teacher_request in queryset.exclude(status=TeacherAccessRequest.STATUS_APPROVED):
            teacher_request.approve(
                reviewer=request.user,
                comment=teacher_request.review_comment,
            )

    @admin.action(description="Отклонить выбранные заявки")
    def reject_requests(self, request, queryset):
        for teacher_request in queryset.exclude(status=TeacherAccessRequest.STATUS_REJECTED):
            teacher_request.reject(
                reviewer=request.user,
                comment=teacher_request.review_comment,
            )
