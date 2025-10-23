from django.urls import path
from .views.submissions import submission_list, submission_detail, submission_compare
from . import views_legacy
from .views.main_page import main_page
from .views.authorization import register_view, login_view, home_view
from .views.tasks import task_list
from .views.contest_draft import create_contest, contest_success
from .views import (
    notebook_list,
    create_notebook,
    notebook_detail,
    create_cell,
    delete_cell,
    save_cell_output,
)


urlpatterns = [
    # GET /runner/api/reports/ - получить список всех отчётов
    path('api/reports/', views_legacy.get_reports_list, name='reports-list'),
    # POST /runner/api/reports/create/ - создать новый отчёт
    path('api/reports/create/', views_legacy.receive_test_result, name='receive-test-result'),
    path("", main_page, name="task_list"),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('task/<int:task_id>/submissions/', submission_list, name="submission_list"),
    path('submission/<int:submission_id>/', submission_detail, name="submission_detail"),
    path('task/<int:task_id>/compare/', submission_compare, name="submission_compare"),
    path("tasks/<int:task_id>/", views_legacy.task_detail, name="task_detail"),
    path("tasks/", task_list, name="task_list"),
    path('contest/new/', create_contest, name='create_contest'),
    path('contest/success/', contest_success, name='contest_success'),
    path('notebook', notebook_list, name='notebook_list'),
    path('notebook/new/', create_notebook, name='create_notebook'),
    path('notebook/<int:notebook_id>/', notebook_detail, name='notebook_detail'),
    path('notebook/<int:notebook_id>/cell/new/', create_cell, name='create_cell'),
    path('notebook/<int:notebook_id>/cell/<int:cell_id>/delete/', delete_cell, name='delete_cell'),
    path('notebook/<int:notebook_id>/cell/<int:cell_id>/save_output/', save_cell_output, name='save_cell_output'),
]
