from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from .models import Task

def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    return render(request, "runner/task_detail.html", {"task": task})