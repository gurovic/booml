from django.shortcuts import render
from ..models import Problem

def problem_list(request):
    problems = Problem.objects.all().only("title", "condition", "created_at")
    return render(request, "runner/list_of_problems.html", {"problems": problems})
