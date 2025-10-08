from django.urls import path
from .views.main_page import main_page
from .views.authorization import register_view, login_view, home_view

urlpatterns = [
    path("", main_page, name="task_list"),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login')
]

