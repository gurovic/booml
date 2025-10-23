from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from runner.models import Task, Submission

@login_required
def submission_list(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    submissions = Submission.objects.filter(task=task, user=request.user).order_by("-created_at")

    if submissions.exists():
        latest_submission = submissions.first()
        context = {
            "task": task,
            "submissions": submissions,
            "result": {
                "status": latest_submission.status,
                "metric": latest_submission.metric,
            }
        }
    else:
        context = {
            "task": task,
            "submissions": [],
            "result": None
        }

    return render(request, "runner/submissions/list.html", context)
