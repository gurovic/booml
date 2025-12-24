from pathlib import Path

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from ..models.problem import Problem
from ..models.problem_desriptor import ProblemDescriptor
from ..models.problem_data import ProblemData
from ..services.metrics import get_available_metrics
#A
MIN_RATING = None
MAX_RATING = None
rating_field = Problem._meta.get_field("rating")
for v in getattr(rating_field, "validators", []):
    limit = getattr(v, "limit_value", None)
    name = v.__class__.__name__.lower()
    if "min" in name:
        MIN_RATING = limit
    if "max" in name:
        MAX_RATING = limit

METRIC_SUGGESTIONS = tuple(get_available_metrics())
METRIC_SUGGESTIONS_SET = set(METRIC_SUGGESTIONS)

DATA_FILE_EXTENSIONS = {".csv", ".zip", ".rar"}
CSV_ONLY_EXTENSIONS = {".csv"}
UPLOAD_FIELD_LABELS = {
    "train_file": "train",
    "test_file": "test",
    "sample_submission_file": "sample submission",
    "answer_file": "answer",
}
UPLOAD_ALLOWED_EXTENSIONS = {
    "train_file": DATA_FILE_EXTENSIONS,
    "test_file": DATA_FILE_EXTENSIONS,
    "sample_submission_file": CSV_ONLY_EXTENSIONS,
    "answer_file": CSV_ONLY_EXTENSIONS,
}


def _format_extensions(extensions):
    return "/".join(ext.lstrip(".").upper() for ext in sorted(extensions))


@require_http_methods(["GET", "POST"])
def edit_problem_polygon(request, problem_id):
    if not request.user.is_authenticated:
        return redirect("runner:login")

    problem = get_object_or_404(Problem, pk=problem_id, author=request.user)
    descriptor = ProblemDescriptor.objects.filter(problem=problem).first()
    problem_data = ProblemData.objects.filter(problem=problem).first()

    def _descriptor_default(field_name):
        field = ProblemDescriptor._meta.get_field(field_name)
        default = field.default
        return default() if callable(default) else default

    form_data = {
        "title": problem.title,
        "rating": str(problem.rating),
        "statement": problem.statement,
    }
    descriptor_form_data = {
        "id_column": descriptor.id_column if descriptor else _descriptor_default("id_column"),
        "target_column": descriptor.target_column if descriptor else _descriptor_default("target_column"),
        "id_type": descriptor.id_type if descriptor else _descriptor_default("id_type"),
        "target_type": descriptor.target_type if descriptor else _descriptor_default("target_type"),
        "check_order": descriptor.check_order if descriptor else _descriptor_default("check_order"),
        "metric_name": descriptor.metric_name if descriptor else _descriptor_default("metric_name"),
        "metric_code": descriptor.metric_code if descriptor else _descriptor_default("metric_code"),
    }
    errors = {}
    descriptor_errors = {}

    if request.method == "POST":
        form_data["title"] = (request.POST.get("title") or "").strip()
        form_data["rating"] = (request.POST.get("rating") or "").strip()
        form_data["statement"] = request.POST.get("statement") or ""

        if not form_data["title"]:
            errors["title"] = "Название обязательно"

        rating_value = None
        try:
            rating_value = int(form_data["rating"])
        except (TypeError, ValueError):
            errors["rating"] = "Рейтинг должен быть целым числом"
        else:
            if not (MIN_RATING <= rating_value <= MAX_RATING):
                errors["rating"] = f"Рейтинг должен быть от {MIN_RATING} до {MAX_RATING}"

        descriptor_form_data["id_column"] = (request.POST.get("id_column") or "").strip()
        descriptor_form_data["target_column"] = (request.POST.get("target_column") or "").strip()
        descriptor_form_data["id_type"] = (request.POST.get("id_type") or "").strip()
        descriptor_form_data["target_type"] = (request.POST.get("target_type") or "").strip()
        descriptor_form_data["check_order"] = request.POST.get("check_order") == "on"
        descriptor_form_data["metric_name"] = (request.POST.get("metric_name") or "").strip()
        descriptor_form_data["metric_code"] = (request.POST.get("metric_code") or "").strip()

        if not descriptor_form_data["id_column"]:
            descriptor_errors["id_column"] = "Колонка идентификатора обязательна"
        if not descriptor_form_data["target_column"]:
            descriptor_errors["target_column"] = "Колонка ответа обязательна"

        id_type_choices = {choice for choice, _ in ProblemDescriptor._meta.get_field("id_type").choices}
        target_type_choices = {choice for choice, _ in ProblemDescriptor._meta.get_field("target_type").choices}

        if descriptor_form_data["id_type"] not in id_type_choices:
            descriptor_errors["id_type"] = "Неверный тип идентификатора"

        if descriptor_form_data["target_type"] not in target_type_choices:
            descriptor_errors["target_type"] = "Неверный тип ответа"

        if not descriptor_form_data["metric_name"]:
            descriptor_errors["metric_name"] = "Укажите метрику"
        elif (
            not descriptor_form_data["metric_code"]
            and descriptor_form_data["metric_name"] not in METRIC_SUGGESTIONS_SET
        ):
            descriptor_errors["metric_name"] = "Выберите метрику из списка или добавьте Python код"

        uploaded_files = {}
        file_errors = {}
        for field_name in ("train_file", "test_file", "sample_submission_file", "answer_file"):
            file_obj = request.FILES.get(field_name)
            if not file_obj:
                continue
            filename = getattr(file_obj, "name", "") or ""
            ext = Path(filename).suffix.lower()
            allowed_extensions = UPLOAD_ALLOWED_EXTENSIONS.get(field_name, CSV_ONLY_EXTENSIONS)
            if ext not in allowed_extensions:
                label = UPLOAD_FIELD_LABELS.get(field_name, field_name)
                allowed_label = _format_extensions(allowed_extensions)
                file_errors[field_name] = f"Файл {label} должен быть в формате {allowed_label}"
            else:
                uploaded_files[field_name] = file_obj

        if file_errors:
            for error_message in file_errors.values():
                messages.error(request, error_message)

        if not errors and not descriptor_errors and not file_errors:
            problem.title = form_data["title"]
            problem.rating = rating_value
            problem.statement = form_data["statement"]
            problem.save(update_fields=["title", "rating", "statement"])

            ProblemDescriptor.objects.update_or_create(
                problem=problem,
                defaults={
                    "id_column": descriptor_form_data["id_column"],
                    "target_column": descriptor_form_data["target_column"],
                    "id_type": descriptor_form_data["id_type"],
                    "target_type": descriptor_form_data["target_type"],
                    "check_order": descriptor_form_data["check_order"],
                    "metric_name": descriptor_form_data["metric_name"],
                    "metric_code": descriptor_form_data["metric_code"],
                },
            )

            if uploaded_files:
                problem_data, _ = ProblemData.objects.get_or_create(problem=problem)
                for field_name, file_obj in uploaded_files.items():
                    setattr(problem_data, field_name, file_obj)
                problem_data.save()

            return redirect("runner:polygon_edit_problem", problem_id=problem.id)

    return render(
        request,
        "runner/polygon/problem_edit.html",
        {
            "problem": problem,
            "form_data": form_data,
            "errors": errors,
            "descriptor_form_data": descriptor_form_data,
            "descriptor_errors": descriptor_errors,
            "id_type_choices": ProblemDescriptor._meta.get_field("id_type").choices,
            "target_type_choices": ProblemDescriptor._meta.get_field("target_type").choices,
            "metric_suggestions": METRIC_SUGGESTIONS,
            "min_rating": MIN_RATING,
            "max_rating": MAX_RATING,
            "problem_data": problem_data,
        },
    )
