from django.urls import path
from . import views
from .views.main_page import main_page
from .views.authorization import register_view, login_view, home_view
from .views import task_detail
from .views.tasks import task_list


urlpatterns = [
    # GET /runner/api/reports/ - получить список всех отчётов
    path('api/reports/', views.get_reports_list, name='reports-list'),
    # POST /runner/api/reports/create/ - создать новый отчёт
    path('api/reports/create/', views.receive_test_result, name='receive-test-result'),
    path("", main_page, name="task_list"),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path("tasks/<int:task_id>/", task_detail, name="task_detail"),
    path("tasks/", task_list, name="task_list"),
]
