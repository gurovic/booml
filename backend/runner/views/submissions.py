from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from runner.models import Task, Submission

def extract_labels_and_metrics(submissions):
    labels = [s.created_at.strftime("%d.%m %H:%M") for s in submissions]
    metrics = [s.metric if s.metric is not None else 0 for s in submissions]
    return labels, metrics

@login_required
def submission_list(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    submissions = Submission.objects.filter(task=task, user=request.user).order_by("created_at")

    result = {}
    if submissions.exists():
        ok_submissions = submissions.filter(status="OK")
        if ok_submissions.exists():
            best_ok = ok_submissions.order_by("-metric").first()
            result = {
                "status": "OK",
                "metric": best_ok.metric
            }
        else:
            best_metric = submissions.filter(metric__isnull=False).order_by("-metric").first()
            last_metric = submissions.last()
            result = {
                "status": "FAILED",
                "best_metric": best_metric.metric if best_metric else None,
                "last_metric": last_metric.metric if last_metric else None,
            }

    labels, metrics = extract_labels_and_metrics(submissions)

    return render(request, "runner/submissions/list.html", {
        "task": task,
        "submissions": submissions.order_by("-created_at"),
        "labels": labels,
        "metrics": metrics,
        "result": result
    })



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
    submissions = Submission.objects.filter(task=task, user=request.user, id__in=ids).order_by("created_at")

    labels, metrics = extract_labels_and_metrics(submissions)

    return render(request, "runner/submissions/compare.html", {
        "task": task,
        "submissions": submissions,
        "labels": labels,
        "metrics": metrics,
    })
