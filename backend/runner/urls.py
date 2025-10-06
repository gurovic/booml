from django.urls import path
from .views.main_page import main_page

urlpatterns = [
    path("", main_page, name="task_list"),
]