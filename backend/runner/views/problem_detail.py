from django.shortcuts import render, get_object_or_404

from runner.api.views import build_descriptor_from_problem

from ..forms import SubmissionUploadForm
from ..models.problem import Problem
from ..models.problem_data import ProblemData
from ..models.submission import Submission
from ..services import enqueue_submission_for_evaluation, validation_service


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


def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    problem_data = ProblemData.objects.filter(problem=problem).first()

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

    context = {
        "problem": problem,
        "data": problem_data,
        "form": form,
        "submission_feedback": submission_feedback,
    }
    return render(request, "runner/problem_detail.html", context)
