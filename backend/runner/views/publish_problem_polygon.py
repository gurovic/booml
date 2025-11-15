from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from ..models.problem import Problem
from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor


@require_http_methods(["POST"])
def publish_problem_polygon(request, problem_id):
    if not request.user.is_authenticated:
        return redirect("runner:login")

    problem = get_object_or_404(Problem, pk=problem_id, author=request.user)

    if problem.is_published:
        messages.info(request, "Задача уже опубликована")
        return redirect("runner:polygon_edit_problem", problem_id=problem.id)

    errors = []

    if not (problem.title or "").strip():
        errors.append("Заполните название задачи")

    if problem.rating is None:
        errors.append("Заполните рейтинг задачи")

    if not (problem.statement or "").strip():
        errors.append("Заполните условие задачи")

    descriptor = ProblemDescriptor.objects.filter(problem=problem).first()
    if not descriptor:
        errors.append("Заполните описание данных (descriptor)")
    else:
        for field_name in ("id_column", "target_column", "id_type", "target_type"):
            value = getattr(descriptor, field_name, "")
            if not value:
                errors.append("Заполните описание данных (descriptor)")
                break

    data = ProblemData.objects.filter(problem=problem).first()
    if not data or not data.answer_file:
        errors.append("Добавьте файл ответов answer.csv")
    elif not data.answer_file.name.lower().endswith(".csv"):
        errors.append("Файл ответов должен быть в формате CSV (answer.csv)")

    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect("runner:polygon_edit_problem", problem_id=problem.id)

    problem.is_published = True
    problem.save(update_fields=["is_published"])
    messages.success(request, "Задача опубликована")

    return redirect("runner:polygon_edit_problem", problem_id=problem.id)
