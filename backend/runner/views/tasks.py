from django.shortcuts import render
from django.core.paginator import Paginator
from ..models import Task

def task_list(request):
    qs = Task.objects.only("title", "statement", "created_at").order_by("-created_at")
    paginator = Paginator(qs, 10)  # 10 задач на страницу
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "runner/task_list.html", {"page_obj": page_obj})
