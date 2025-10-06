# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.code_runner_template, name='code_runner_page'),
    path('run', views.code_run_api, name='code_run_api'),
]
