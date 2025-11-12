from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.utils.text import Truncator

from ..models.problem import Problem


@require_http_methods(["GET", "POST"])
def create_problem_polygon(request):
    if request.method == "GET":
        return render(request, "runner/polygon/problem_create.html")

    is_json = (request.content_type or "").startswith("application/json")

    title = request.POST.get("title")
    if not title and is_json:
        try:
            import json
            payload = json.loads(request.body.decode("utf-8") or "{}")
            title = payload.get("title")
        except Exception:
            title = None

    if not title or not str(title).strip():
        if is_json:
            return JsonResponse({
                "status": "error",
                "message": "Поле 'title' обязательно и не может быть пустым."
            }, status=400)
        return render(
            request,
            "runner/polygon/problem_create.html",
            {"error": "Введите название задачи", "title_value": (title or "").strip()}
        )

    title = str(title).strip()
    if len(title) > 255:
        title = Truncator(title).chars(255)

    if not request.user.is_authenticated:
        return redirect("runner:login")

    author = request.user
    problem = Problem.objects.create(title=title, author=author, is_published=False)

    if is_json:
        return JsonResponse({"status": "success", "problem_id": problem.id})

    return redirect("runner:polygon")
