from django.shortcuts import render
from runner.models.task import Task     

def home(request):
    user = request.user if request.user.is_authenticated else None
    tasks = Task.objects.all()
    return render(request, "core/home.html", {
        "user": user,
        "tasks": tasks
    })
