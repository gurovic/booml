from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from ..models.problem import Problem

MIN_RATING = 800
MAX_RATING = 3000


@require_http_methods(["GET", "POST"])
def edit_problem_polygon(request, problem_id):
    if not request.user.is_authenticated:
        return redirect("runner:login")

    problem = get_object_or_404(Problem, pk=problem_id, author=request.user)

    form_data = {
        "title": problem.title,
        "rating": str(problem.rating),
        "statement": problem.statement,
    }
    errors = {}

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

        if not errors:
            problem.title = form_data["title"]
            problem.rating = rating_value
            problem.statement = form_data["statement"]
            problem.save(update_fields=["title", "rating", "statement"])
            return redirect("runner:polygon_edit_problem", problem_id=problem.id)

    return render(
        request,
        "runner/polygon/problem_edit.html",
        {"problem": problem, "form_data": form_data, "errors": errors},
    )
