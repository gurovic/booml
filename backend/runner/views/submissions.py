from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from runner.models import Problem, Submission
from django.http.response import HttpResponseBadRequest

@login_required
def submission_list(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    submissions = Submission.objects.filter(problem=problem, user=request.user).order_by("-created_at")

    if submissions.exists():
        latest_submission = submissions.first()
        context = {
            "problem": problem,
            "submissions": submissions,
            "result": {
                "status": latest_submission.status,
                "metric": latest_submission.metric,
            }
        }
    else:
        context = {
            "problem": problem,
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
def submission_compare(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)

    ids = request.GET.getlist("ids")
    ids = [int(i) for i in ids if i.isdigit()]
    if not ids:
        return HttpResponseBadRequest("No valid submission IDs provided.")
    submissions = Submission.objects.filter(problem=problem, user=request.user, id__in=ids).order_by("created_at")

    labels, metrics = extract_labels_and_metrics(submissions)

    return render(request, "runner/submissions/compare.html", {
        "problem": problem,
        "submissions": submissions,
        "labels": labels,
        "metrics": metrics,
    })