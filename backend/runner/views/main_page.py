from django.shortcuts import render
from ..models import Task

def main_page(request):
    tasks = Task.objects.only("title", "statement", "created_at","rating").order_by("?")[:15]
    return render(request, "runner/main_page.html", {"tasks": tasks})
