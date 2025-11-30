from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from ..models import Course
from ..forms.contest_draft import ContestForm

@login_required
def create_contest(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if request.method == 'POST':
        form = ContestForm(request.POST, course=course)
        if form.is_valid():
            form.save(created_by=request.user, course=course)
            return redirect('contest/success')  # имя URL для страницы успеха
    else:
        form = ContestForm(course=course)

    return render(request, 'runner/contest/contest_form.html', {'form': form, 'course': course})

@login_required
def contest_success(request):
    return render(request, 'runner/contest/contest_success.html')
