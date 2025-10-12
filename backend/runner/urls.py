from django.urls import path
from . import views

urlpatterns = [
    # GET /runner/api/reports/ - получить список всех отчётов
    path('api/reports/', views.get_reports_list, name='reports-list'),
    # POST /runner/api/reports/create/ - создать новый отчёт
    path('api/reports/create/', views.receive_test_result, name='receive-test-result'),
]