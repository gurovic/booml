from django.urls import path
from .views.main_page import main_page
from .views.authorization import register_view, login_view, home_view
from .views import task_detail
from .views.tasks import task_list

urlpatterns = [
    path("", main_page, name="task_list"),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path("tasks/<int:task_id>/", task_detail, name="task_detail"),
    path("tasks/", task_list, name="task_list"),
]

