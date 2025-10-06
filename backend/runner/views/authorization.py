from django.shortcuts import render, redirect
from django.contrib.auth import login
from runner.forms.authorization import RegisterForm
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
    return HttpResponse('The login page is currently under development')
