from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .forms.submit_problem import SubmissionForm

@login_required
def create_submission(request, problem_id):
    if request.method == "POST":
        form = SubmissionForm(request.POST, request.FILES)
        print(problem_id)
        if form.is_valid():
            print('12312312321')
            submission = form.save(commit=False)
            
            submission.user = request.user
            submission.save()
            return redirect(reverse("problem_detail", args=[problem_id]))

    else:
        form = SubmissionForm()
        return render(request, "mainsite/problem.html", {"form": form,"problem_id":problem_id})
