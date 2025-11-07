from django.shortcuts import render

from ..models import Problem


def main_page(request):
    problems = Problem.objects.only("title", "statement", "created_at", "rating").order_by("?")[:15]
    context = {
        "problems": problems,
        "tasks": problems,  # include alias expected by the shared template fragment
    }
    return render(request, "runner/main_page.html", context)
