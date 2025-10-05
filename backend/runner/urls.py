from django.urls import path
from .views.list_of_problems import problem_list

app_name = "runner"

urlpatterns = [
    path("", problem_list, name="problem_list"),
]