from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from ..models.problem import Problem
from ..models.problem_desriptor import ProblemDescriptor
from ..models.problem_data import ProblemData

MIN_RATING = 800
MAX_RATING = 3000


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

        uploaded_files = {}
        for field_name in ("train_file", "test_file", "sample_submission_file", "answer_file"):
            file_obj = request.FILES.get(field_name)
            if file_obj:
                uploaded_files[field_name] = file_obj

        if not errors and not descriptor_errors:
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
            "problem_data": problem_data,
        },
    )
