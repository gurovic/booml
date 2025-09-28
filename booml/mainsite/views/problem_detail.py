from django.shortcuts import render, get_object_or_404
from mainsite.models import Problem

def problem_detail(request, pk):
    """
    Отдаёт страницу с полным условием одной задачи.
    Ожидает в URL параметр pk — первичный ключ (id) объекта Problem.
    """
    problem = get_object_or_404(Problem, pk=pk)
    return render(request, "mainsite/problem_detail.html", {"problem": problem})
