import random
from django.shortcuts import render

ALL_TASKS = [
    {"id": 1, "title": "Задача 1"},
    {"id": 2, "title": "Задача 2"},
    {"id": 3, "title": "Задача 3"},
    {"id": 4, "title": "Задача 4"},
    {"id": 5, "title": "Задача 5"},
    {"id": 6, "title": "Задача 6"},
    {"id": 7, "title": "Задача 7"},
    {"id": 8, "title": "Задача 8"},
    {"id": 9, "title": "Задача 9"},
    {"id": 10, "title": "Задача 10"},
    {"id": 11, "title": "Задача 11"},
    {"id": 12, "title": "Задача 12"},
    {"id": 13, "title": "Задача 13"},
    {"id": 14, "title": "Задача 14"},
    {"id": 15, "title": "Задача 15"},
    {"id": 16, "title": "Задача 16"},
    {"id": 17, "title": "Задача 17"},
    {"id": 18, "title": "Задача 18"},
    {"id": 19, "title": "Задача 19"},
    {"id": 20, "title": "Задача 20"},
]

def home(request):
    user = request.user if request.user.is_authenticated else None
    tasks = random.sample(ALL_TASKS, min(15, len(ALL_TASKS)))
    return render(request, "core/home.html", {
        "user": user,
        "tasks": tasks
    })
