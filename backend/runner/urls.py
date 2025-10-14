from django.urls import path
from .views.submissions import submission_list, submission_detail, submission_compare
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
    path('task/<int:task_id>/submissions/', submission_list, name="submission_list"),
    path('submission/<int:submission_id>/', submission_detail, name="submission_detail"),
    path('task/<int:task_id>/compare/', submission_compare, name="submission_compare"),
    path("tasks/<int:task_id>/", task_detail, name="task_detail"),
    path("tasks/", task_list, name="task_list"),
]
