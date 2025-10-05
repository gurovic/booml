from django.urls import path
from .views.authorization import register_view, login_view

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login')
]
