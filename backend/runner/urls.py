from django.urls import path
from . import views

urlpatterns = [
    path('run-checks/', views.run_checks_view, name='run_checks'),
    path('reports/', views.get_reports_list, name='reports_list'),
    path('reports/<int:report_id>/json/', views.get_report_json, name='report_json'),
]