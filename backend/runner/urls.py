from django.urls import path
from .views.main_page import main_page
from .views.authorization import register_view, login_view, home_view
from .views import task_detail, task_pdf

urlpatterns = [
    path("", main_page, name="task_list"),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path("tasks/<int:task_id>/", task_detail, name="task_detail"),
    path("tasks/<int:task_id>/pdf/", task_pdf, name="task_pdf"),
]