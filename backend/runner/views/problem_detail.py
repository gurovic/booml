from django.shortcuts import render, get_object_or_404

from runner.api.views import build_descriptor_from_problem

from ..forms import SubmissionUploadForm
from ..models.problem import Problem
from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor
from ..models.submission import Submission
from ..models.notebook import Notebook
from ..services import enqueue_submission_for_evaluation, validation_service
from ..services.problem_scoring import (
    default_curve_p,
    extract_raw_metric,
    extract_score_100,
    resolve_score_spec,
    score_from_raw,
)
from .submissions import submission_list, _primary_metric
from django.http import JsonResponse
from django.utils import timezone
from zoneinfo import ZoneInfo


def _report_is_valid(report) -> bool:
    """
    Унифицированная проверка статуса отчёта предварительной валидации.
    """
    if report is None:
        return True

    for attr in ("is_valid", "valid"):
        value = getattr(report, attr, None)
        if value is not None:
            return bool(value)

    status = getattr(report, "status", None)
    if isinstance(status, str):
        return status.lower() not in {"failed", "error"}

    return True


def _submission_score(submission: Submission) -> float | None:
    metrics = getattr(submission, "metrics", None)
    score_100 = extract_score_100(metrics)
    if score_100 is not None:
        return float(score_100)

    descriptor = getattr(getattr(submission, "problem", None), "descriptor", None)
    metric_name = "metric"
    if isinstance(metrics, dict):
        raw_metric_name = metrics.get("raw_metric_name")
        if isinstance(raw_metric_name, str) and raw_metric_name.strip():
            metric_name = raw_metric_name.strip()
    if descriptor is not None:
        descriptor_metric = getattr(descriptor, "metric", "")
        descriptor_metric_name = getattr(descriptor, "metric_name", "")
        if isinstance(descriptor_metric, str) and descriptor_metric.strip():
            metric_name = descriptor_metric.strip()
        elif isinstance(descriptor_metric_name, str) and descriptor_metric_name.strip():
            metric_name = descriptor_metric_name.strip()

    raw_metric = extract_raw_metric(metrics, metric_name=metric_name)
    if raw_metric is None:
        return _primary_metric(metrics)

    score_spec = resolve_score_spec(
        metric_name,
        descriptor_direction=getattr(descriptor, "score_direction", "") if descriptor else "",
        descriptor_ideal=getattr(descriptor, "score_ideal_metric", None) if descriptor else None,
    )
    reference_metric = getattr(descriptor, "score_reference_metric", None) if descriptor else None
    curve_p = getattr(descriptor, "score_curve_p", None) if descriptor else None
    nonlinear_reference = (
        float(reference_metric)
        if isinstance(reference_metric, (int, float))
        and abs(float(reference_metric) - float(score_spec.ideal)) > 1e-12
        else None
    )
    nonlinear_curve = (
        float(curve_p)
        if isinstance(curve_p, (int, float))
        else default_curve_p(score_spec.direction)
    )
    score_100, _ = score_from_raw(
        float(raw_metric),
        metric_name=metric_name,
        direction=score_spec.direction,
        ideal=float(score_spec.ideal),
        reference=nonlinear_reference,
        curve_p=nonlinear_curve,
    )
    return float(score_100)


def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    problem_data = ProblemData.objects.filter(problem=problem).first()
    descriptor = ProblemDescriptor.objects.filter(problem=problem).first()

    form = SubmissionUploadForm()
    submission_feedback = None

    if request.method == "POST":
        if not request.user.is_authenticated:
            submission_feedback = {
                "level": "error",
                "message": "Авторизуйтесь, чтобы отправить решение.",
            }
        else:
            form = SubmissionUploadForm(request.POST, request.FILES)
            if form.is_valid():
                submission = Submission.objects.create(
                    user=request.user,
                    problem=problem,
                    file=form.cleaned_data["file"],
                )

                descriptor = build_descriptor_from_problem(problem)
                try:
                    report = validation_service.run_pre_validation(submission, descriptor=descriptor)
                except Exception as exc:  # pragma: no cover - defensive
                    submission_feedback = {
                        "level": "error",
                        "message": "Не удалось запустить предварительную проверку.",
                        "details": str(exc),
                    }
                else:
                    if _report_is_valid(report):
                        enqueue_submission_for_evaluation(submission.id)
                        submission_feedback = {
                            "level": "success",
                            "message": "Файл отправлен в тестирующую систему. Проверка начнётся в ближайшее время.",
                        }
                        form = SubmissionUploadForm()
                    else:
                        details = None
                        errors = getattr(report, "errors", None)
                        if errors:
                            details = errors[0] if isinstance(errors, list) else str(errors)

                        submission_feedback = {
                            "level": "error",
                            "message": "Файл не прошёл предварительную проверку.",
                            "details": details,
                        }
            else:
                submission_feedback = {
                    "level": "error",
                    "message": "Исправьте ошибки формы и попробуйте снова.",
                }

    if request.user.is_authenticated:
        context_submissions_list = submission_list(request, problem_id, as_context=True, limit=5)
    else:
        context_submissions_list = {
            "submissions": [],
            "result": None
        }

    context = {
        "problem": problem,
        "data": problem_data,
        "descriptor": descriptor,
        "form": form,
        "submission_feedback": submission_feedback,
        "submissions": context_submissions_list["submissions"],
        "result": context_submissions_list["result"]
    }
    return render(request, "runner/problem_detail.html", context)


def problem_detail_api(request):
    problem_id = request.GET.get('problem_id')

    if problem_id is None:
        return JsonResponse({'error': 'problem_id is required'}, status=400)

    problem = get_object_or_404(Problem, id=problem_id)
    problem_data = ProblemData.objects.filter(problem=problem).first()
    descriptor = ProblemDescriptor.objects.filter(problem=problem).first()

    def get_file_url(file):
        """Return relative URL path for frontend proxy to handle."""
        if not file:
            return None
        # Return relative URL (e.g., /media/problem_data/1/train/file.csv)
        # The frontend proxy will route this to the backend
        return file.url
    
    file_urls = {
        "train": None,
        "test": None,
        "sample_submission": None
    }

    if problem_data:
        file_urls = {
            "train": get_file_url(problem_data.train_file),
            "test": get_file_url(problem_data.test_file),
            "sample_submission": get_file_url(problem_data.sample_submission_file)
        }

    submissions = []
    notebook_id = None
    
    if request.user.is_authenticated:
        raw_submissions = (
            Submission.objects
            .filter(problem=problem, user=request.user)
            .order_by("-submitted_at")[:5]
        )

        for submission in raw_submissions:
            metric_value = _submission_score(submission)
            submitted = submission.submitted_at
            if submitted:
                submitted = timezone.localtime(submitted, ZoneInfo("Europe/Moscow"))
            submissions.append({
                "id": submission.id,
                "submitted_at": submitted.strftime("%H:%M") if submitted else None,
                "status": submission.status,
                "metric": metric_value,
                "score": metric_value,
                "metrics": submission.metrics,
            })
        
        # Get user's notebook for this problem
        user_notebook = Notebook.objects.filter(
            owner=request.user,
            problem=problem
        ).first()
        
        if user_notebook:
            notebook_id = user_notebook.id

    response = {
        "id": problem.id,
        "title": problem.title,
        "statement": problem.statement,
        "files": file_urls,
        "submissions": submissions,
        "notebook_id": notebook_id,
    }

    return JsonResponse(response)
