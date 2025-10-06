from django.urls import path
from .views import run_view
urlpatterns = [ path("run", run_view) ]