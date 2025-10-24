from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from runner.models import Task, Submission
from django.http.response import HttpResponseBadRequest

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

def extract_labels_and_metrics(submissions):
    labels = [s.created_at.strftime("%d.%m %H:%M") for s in submissions]
    metrics = [s.metric if s.metric is not None else 0 for s in submissions]
    return labels, metrics

@login_required
def submission_detail(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id, user=request.user)
    return render(request, "runner/submissions/detail.html", {
        "submission": submission
    })

@login_required
def submission_compare(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    ids = request.GET.getlist("ids")
    ids = [int(i) for i in ids if i.isdigit()]
    if not ids:
        return HttpResponseBadRequest("No valid submission IDs provided.")
    submissions = Submission.objects.filter(task=task, user=request.user, id__in=ids).order_by("created_at")

    labels, metrics = extract_labels_and_metrics(submissions)

    return render(request, "runner/submissions/compare.html", {
        "task": task,
        "submissions": submissions,
        "labels": labels,
        "metrics": metrics,
    })