from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from runner.api.views import build_descriptor_from_problem

from ..forms import SubmissionUploadForm
from ..models.notebook import Notebook
from ..models.problem import Problem
from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor
from ..models.submission import Submission
from ..services import enqueue_submission_for_evaluation, validation_service
from .submissions import _primary_metric, submission_list

PUBLIC_PROBLEM_FILE_KINDS = ("train", "test", "sample_submission")
PROBLEM_FILE_KIND_TO_FIELD = {
    "train": "train_file",
    "test": "test_file",
    "sample_submission": "sample_submission_file",
}
PROBLEM_FILE_KIND_ORDER = {kind: idx for idx, kind in enumerate(PUBLIC_PROBLEM_FILE_KINDS)}
CANONICAL_PUBLIC_NAMES = {
    "train": "train.csv",
    "test": "test.csv",
    "sample_submission": "sample_submission.csv",
}
KIND_KEYWORDS = {
    "train": ("train",),
    "test": ("test",),
    "sample_submission": ("sample", "submission", "template"),
}


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


def _problem_data_root() -> Path:
    return Path(settings.PROBLEM_DATA_ROOT)


def _media_problem_data_root() -> Path:
    return Path(settings.MEDIA_ROOT) / "problem_data"


def _problem_file_roots() -> list[Path]:
    primary = _problem_data_root()
    legacy = _media_problem_data_root()
    if legacy == primary:
        return [primary]
    return [primary, legacy]


def _is_valid_public_file_kind(kind: str | None) -> bool:
    return isinstance(kind, str) and kind in PROBLEM_FILE_KIND_TO_FIELD


def _is_valid_public_file_name(name: str | None) -> bool:
    if not isinstance(name, str):
        return False
    if not name or name in {".", ".."}:
        return False
    if "/" in name or "\\" in name or "\x00" in name:
        return False
    return Path(name).name == name


def _is_answer_like_name(name: str) -> bool:
    return "answer" in name.lower()


def _canonical_public_name(kind: str, source_name: str) -> str:
    _ = source_name
    return CANONICAL_PUBLIC_NAMES[kind]


def _list_root_problem_files(problem_id: int, kind: str) -> list[Path]:
    files: list[Path] = []
    seen_names: set[str] = set()

    for root in _problem_file_roots():
        kind_dir = root / str(problem_id) / kind
        if not kind_dir.exists() or not kind_dir.is_dir():
            continue

        root_files = sorted((p for p in kind_dir.iterdir() if p.is_file()), key=lambda p: (p.name.lower(), p.name))
        for file_path in root_files:
            if file_path.name in seen_names:
                continue
            seen_names.add(file_path.name)
            files.append(file_path)

    return files


def _get_problem_data_fallback_file(problem_data: ProblemData | None, kind: str):
    if not problem_data:
        return None

    field_name = PROBLEM_FILE_KIND_TO_FIELD.get(kind)
    if not field_name:
        return None

    file_field = getattr(problem_data, field_name, None)
    if not file_field or not getattr(file_field, "name", None):
        return None

    try:
        if not file_field.storage.exists(file_field.name):
            return None
    except Exception:
        return None

    return file_field


def _build_problem_file_download_url(problem_id: int, kind: str, name: str) -> str:
    base_url = reverse("runner:backend_problem_file_download", args=[problem_id])
    return f"{base_url}?{urlencode({'kind': kind, 'name': name})}"


def _collect_kind_candidates(problem: Problem, kind: str, problem_data: ProblemData | None) -> list[dict]:
    candidates: list[dict] = []
    for file_path in _list_root_problem_files(problem.id, kind):
        if _is_answer_like_name(file_path.name):
            continue
        candidates.append({"source": file_path, "name": file_path.name, "source_priority": 0})

    fallback_file = _get_problem_data_fallback_file(problem_data, kind)
    if fallback_file:
        fallback_name = Path(fallback_file.name).name
        if not _is_answer_like_name(fallback_name):
            candidates.append({"source": fallback_file, "name": fallback_name, "source_priority": 1})
    return candidates


def _choose_kind_candidate(kind: str, candidates: list[dict]) -> dict | None:
    if not candidates:
        return None

    keywords = KIND_KEYWORDS.get(kind, ())
    exact_names = {
        CANONICAL_PUBLIC_NAMES[kind].lower(),
        f"{kind}.csv",
        f"{kind}.zip",
        f"{kind}.rar",
        f"{kind}.parquet",
        f"{kind}.parq",
    }

    def rank(candidate: dict):
        name = candidate["name"].lower()
        suffix = Path(candidate["name"]).suffix.lower()
        source_priority = candidate.get("source_priority", 1)
        exact_score = 0 if name in exact_names else 1
        keyword_score = 0 if keywords and any(word in name for word in keywords) else 1
        suffix_score = 0 if suffix == ".csv" else 1
        return (source_priority, exact_score, keyword_score, suffix_score, name)

    return sorted(candidates, key=rank)[0]


def _collect_public_problem_files(problem: Problem, problem_data: ProblemData | None) -> list[dict]:
    files: list[dict] = []

    for kind in PUBLIC_PROBLEM_FILE_KINDS:
        candidates = _collect_kind_candidates(problem, kind, problem_data)
        chosen = _choose_kind_candidate(kind, candidates)
        if not chosen:
            continue
        canonical_name = _canonical_public_name(kind, chosen["name"])
        files.append(
            {
                "kind": kind,
                "name": canonical_name,
                "url": _build_problem_file_download_url(problem.id, kind, canonical_name),
            }
        )

        for submission in raw_submissions:
            metric_value = _primary_metric(submission.metrics)
            submitted = submission.submitted_at
            # Send full ISO format datetime for frontend to format
            submissions.append({
                "id": submission.id,
                "submitted_at": submitted.isoformat() if submitted else None,
                "status": submission.status,
                "metric": metric_value,
                "metrics": submission.metrics,
            })
        
        # Get user's notebook for this problem
        user_notebook = Notebook.objects.filter(
            owner=request.user,
            problem=problem
        ).first()
        
        if user_notebook:
            notebook_id = user_notebook.id
    files.sort(key=lambda item: (PROBLEM_FILE_KIND_ORDER[item["kind"]], item["name"].lower(), item["name"]))
    return files


def _resolve_public_problem_file(problem: Problem, kind: str, name: str, problem_data: ProblemData | None = None):
    candidates = _collect_kind_candidates(problem, kind, problem_data)
    chosen = _choose_kind_candidate(kind, candidates)
    if not chosen:
        return None

    actual_name = chosen["name"]
    canonical_name = _canonical_public_name(kind, actual_name)
    if name not in {actual_name, canonical_name}:
        return None
    return chosen["source"], canonical_name


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
    file_list = _collect_public_problem_files(problem, problem_data)
    file_urls = {kind: None for kind in PUBLIC_PROBLEM_FILE_KINDS}
    for file_item in file_list:
        kind = file_item["kind"]
        if file_urls[kind] is None:
            file_urls[kind] = file_item["url"]

    submissions = []
    notebook_id = None
    
    if request.user.is_authenticated:
        raw_submissions = (
            Submission.objects
            .filter(problem=problem, user=request.user)
            .order_by("-submitted_at")[:5]
        )

        for submission in raw_submissions:
            metric_value = _primary_metric(submission.metrics)
            submitted = submission.submitted_at
            if submitted:
                submitted = timezone.localtime(submitted, ZoneInfo("Europe/Moscow"))
            submissions.append({
                "id": submission.id,
                "submitted_at": submitted.strftime("%H:%M") if submitted else None,
                "status": submission.status,
                "metric": metric_value,
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
        "file_list": file_list,
        "files": file_urls,
        "submissions": submissions,
        "notebook_id": notebook_id,
    }

    return JsonResponse(response)


def problem_file_download_api(request, problem_id: int):
    kind = request.GET.get("kind")
    name = request.GET.get("name")

    if not _is_valid_public_file_kind(kind):
        return JsonResponse({"error": "Invalid file kind"}, status=400)
    if not _is_valid_public_file_name(name):
        return JsonResponse({"error": "Invalid file name"}, status=400)

    problem = get_object_or_404(Problem, id=problem_id)
    problem_data = ProblemData.objects.filter(problem=problem).first()
    resolved_file = _resolve_public_problem_file(problem, kind, name, problem_data=problem_data)
    if resolved_file is None:
        return JsonResponse({"error": "File not found"}, status=404)
    source_file, download_name = resolved_file

    if isinstance(source_file, Path):
        return FileResponse(source_file.open("rb"), as_attachment=True, filename=download_name)

    return FileResponse(
        source_file.open("rb"),
        as_attachment=True,
        filename=download_name,
    )
