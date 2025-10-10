from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from .models import Task

def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    return render(request, "runner/task_detail.html", {"task": task})


def task_pdf(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica", 14)
    pdf.drawString(100, 750, f"Task: {task.title}")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 720, f"Description: {task.description}")
    if task.data:
        pdf.drawString(100, 700, f"Dataset: {task.data}")
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf")