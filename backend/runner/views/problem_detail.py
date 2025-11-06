from django.shortcuts import render, get_object_or_404
from ..models.problem import Problem


def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    return render(request, "runner/problem_detail.html", {"problem": problem})