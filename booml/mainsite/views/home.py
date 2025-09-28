from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .problems_list import *

def home(request):
    """Главная страница с тремя кнопками"""
    context = get_all_problems()
    return render(request, 'mainsite/home.html', context=context)

@login_required
def username(request):
    """Страница профиля пользователя"""
    context = {
        'user': request.user
    }
    return render(request, 'mainsite/profile.html', context=context)

def logout_view(request):
    """Выход пользователя из системы"""
    logout(request)
    return redirect('home')
