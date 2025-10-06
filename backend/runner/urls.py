from django.urls import path
from .views.authorization import register_view, login_view, home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login')
]
