from django.shortcuts import render, redirect
from django.contrib.auth import login
from runner.forms.authorization import RegisterForm, LoginForm
from django.http import HttpResponse


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'runner/authorization/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            return redirect('home')
    else:
        form = LoginForm()

    return render(request, 'runner/authorization/login.html', {'form': form})

def home_view(reqeust):
    return HttpResponse(f'Dear, {reqeust.user.username}, the login page is currently under development')