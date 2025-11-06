from django.shortcuts import render, get_object_or_404
from ..models.problem import Problem
from ..models.problem_data import ProblemData


def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    problem_data = get_object_or_404(ProblemData, problem=problem)
    return render(request, "runner/problem_detail.html", {"problem": problem, "data": problem_data})