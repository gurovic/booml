from django.shortcuts import render, get_object_or_404

from .models import Task


def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    return render(request, "runner/task_detail.html", {"task": task})
