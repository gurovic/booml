from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from runner.models import Problem, Submission
from django.http.response import HttpResponseBadRequest


def _primary_metric(metrics):
    if metrics is None:
        return None
    if isinstance(metrics, (int, float)):
        return float(metrics)
    if isinstance(metrics, dict):
        for key in ("metric", "score", "accuracy", "f1", "auc"):
            if key in metrics:
                try:
                    return float(metrics[key])
                except:
                    return metrics[key]
        for v in metrics.values():
            try:
                return float(v)
            except:
                continue
        return None
    if isinstance(metrics, (list, tuple)):
        for v in metrics:
            try:
                return float(v)
            except:
                continue
        return None
    try:
        return float(metrics)
    except:
        return None


def _enrich_submissions(queryset):
    enriched = []
    for submission in queryset:
        setattr(submission, "created_at", getattr(submission, "submitted_at", None))
        setattr(submission, "metric", _primary_metric(getattr(submission, "metrics", None)))
        enriched.append(submission)
    return enriched


def _latest_result(submissions):
    if not submissions:
        return None
    latest_submission = submissions[0]
    status_map = {"accepted": "OK", "validated": "OK", "failed": "FAILED"}
    result_status = status_map.get(getattr(latest_submission, "status", ""), getattr(latest_submission, "status", ""))
    return {
        "status": result_status,
        "metric": getattr(latest_submission, "metric", None),
    }

@login_required
def submission_list(request, problem_id, *, as_context=False, limit=None):
    problem = get_object_or_404(Problem, id=problem_id)
    submissions_qs = Submission.objects.filter(problem=problem, user=request.user).order_by("-submitted_at")
    submissions = []

    try:
        if submissions_qs.exists():
            try:
                submissions = _enrich_submissions(submissions_qs)
            except Exception:
                submissions = []
    except Exception:
        submissions = []

    context = {
        "problem": problem,
        "submissions": submissions,
        "result": _latest_result(submissions),
        "limit": limit,
    }

    if as_context:
        return context

    response = render(request, "runner/submissions/list.html", context)
    # Expose context for internal callers without TestClient helpers.
    response.context_data = context
    return response

@login_required
def recent_submissions(request):
    submissions_queryset = Submission.objects.filter(user=request.user).select_related("problem").order_by("-submitted_at")[:20]
    submissions = _enrich_submissions(submissions_queryset)
    context = {
        "submissions": submissions,
        "result": _latest_result(submissions),
    }

    return render(request, "runner/submissions/recent.html", context)

def extract_labels_and_metrics(submissions):
    labels = []
    metrics = []
    for s in submissions:
        created = getattr(s, "created_at", getattr(s, "submitted_at", None))
        metric = getattr(s, "metric", _primary_metric(getattr(s, "metrics", None)))
        labels.append(created.strftime("%d.%m %H:%M") if created else "-")
        metrics.append(metric if metric is not None else 0)
    return labels, metrics

@login_required
def submission_detail(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id, user=request.user)
    setattr(submission, "created_at", submission.submitted_at)
    setattr(submission, "metric", _primary_metric(submission.metrics))
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
    submissions = list(Submission.objects.filter(problem=problem, user=request.user, id__in=ids).order_by("submitted_at"))
    for s in submissions:
        setattr(s, "created_at", s.submitted_at)
        setattr(s, "metric", _primary_metric(s.metrics))

    labels, metrics = extract_labels_and_metrics(submissions)

    return render(request, "runner/submissions/compare.html", {
        "problem": problem,
        "submissions": submissions,
        "labels": labels,
        "metrics": metrics,
    })
