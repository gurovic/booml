from django.urls import path
from .views.submissions import submission_list, submission_detail, submission_compare
from .views.main_page import main_page
from .views.authorization import register_view, login_view, home_view
from .views.tasks import task_list

urlpatterns = [
    path("", main_page, name="task_list"),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('task/<int:task_id>/submissions/', submission_list, name="submission_list"),
    path('submission/<int:submission_id>/', submission_detail, name="submission_detail"),
    path('task/<int:task_id>/compare/', submission_compare, name="submission_compare"),
    path("tasks/", task_list, name="task_list"),
]

