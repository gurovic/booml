from django.urls import path
from .views import task_detail, task_pdf

app_name = "runner"

urlpatterns = [
    path("tasks/<int:task_id>/", task_detail, name="task_detail"),
    path("tasks/<int:task_id>/pdf/", task_pdf, name="task_pdf"),
]