from django.shortcuts import render
from django.core.paginator import Paginator
from ..models import Task

def task_list(request):
    tasks = Task.objects.only("title", "created_at", "rating").order_by("-created_at")
    paginator = Paginator(tasks, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "runner/task_list.html", {"page_obj": page_obj})
