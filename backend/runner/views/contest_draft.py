from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ..forms.contest_draft import ContestForm

@login_required
def create_contest(request):
    if request.method == 'POST':
        form = ContestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('contest_success')  # имя URL для страницы успеха
    else:
        form = ContestForm()

    return render(request, 'runner/contest/contest_form.html', {'form': form})

@login_required
def contest_success(request):
    return render(request, 'runner/contest/contest_success.html')
