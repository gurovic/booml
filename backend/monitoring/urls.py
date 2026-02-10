from django.urls import path
from . import views

urlpatterns = [
    path('system/', views.SystemMetricsView.as_view(), name='system-metrics'),
    path('tasks/', views.TaskStatisticsView.as_view(), name='task-statistics'),
    path('historical/', views.HistoricalStatisticsView.as_view(), name='historical-statistics'),
    path('historical-metrics/', views.HistoricalMetricsView.as_view(), name='historical-metrics'),
]