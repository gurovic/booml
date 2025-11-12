from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from ..models.problem import Problem

@require_http_methods(["GET", "POST"])
def create_problem_polygon(request):
    if request.method == "GET":
        return render(request, "runner/polygon/problem_create.html")

    if not request.user.is_authenticated:
        return redirect("runner:login")

    title = (request.POST.get("title") or "").strip()
    if not title:
        return render(request, "runner/polygon/problem_create.html")

    Problem.objects.create(
        title=title,
        author=request.user,
        is_published=False,
    )
    return redirect("runner:polygon")
