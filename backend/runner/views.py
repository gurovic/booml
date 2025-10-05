from django.shortcuts import render
from django.http import Http404

# Тестовые задачи
tasks = [
    {
        "id": 1,
        "title": "MNIST classifier",
        "description": "Predict handwritten digits",
        "data": "mnist.csv",
        "tags": ["classification", "MNIST", "deep learning"]
    },
    {
        "id": 2,
        "title": "Titanic survival",
        "description": "Predict survival",
        "data": "titanic.csv",
        "tags": ["classification", "logistic regression", "tabular data"]
    }
]

def task_detail(request, task_id):
    for task in tasks:
        if task["id"] == task_id:
            return render(request, "runner/task_detail.html", {"task": task})
    raise Http404("Task not found")

# Заглушка для PDF (еще не реализовано)
def task_pdf(request, task_id):
    # пока просто возвращаем текст, можно позже подключить xhtml2pdf или weasyprint
    for task in tasks:
        if task["id"] == task_id:
            from django.http import HttpResponse
            return HttpResponse(f"PDF for task {task['title']} would be generated here.", content_type="text/plain")
    raise Http404("Task not found")