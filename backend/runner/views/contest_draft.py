import json
import uuid
from datetime import datetime, time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from ..models import Contest, Course, Problem, CourseParticipant, ContestProblem, Submission
from ..forms.contest_draft import ContestForm
from ..services.contest_labels import contest_problem_label
from .contest_leaderboard import build_contest_leaderboards
from .submissions import _primary_metric

User = get_user_model()

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off", ""}


def _parse_bool(value, *, default=None):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    return default


def _coerce_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = parse_datetime(value.strip())
    else:
        return None
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _contest_timing_payload(contest: Contest, *, user=None, include_submit=False) -> dict:
    end_time = contest.get_end_time()
    payload = {
        "start_time": contest.start_time.isoformat() if contest.start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "duration_minutes": contest.duration_minutes,
        "has_time_limit": bool(contest.start_time and contest.duration_minutes),
        "allow_upsolving": bool(contest.allow_upsolving),
        "time_state": contest.time_state(),
    }
    if include_submit:
        can_submit, submit_block_reason = contest.is_submission_allowed(user)
        payload["can_submit"] = bool(can_submit)
        payload["submit_block_reason"] = submit_block_reason or None
    return payload


def _contest_questions_enabled(contest: Contest) -> bool:
    return bool(contest.allow_notifications and contest.allow_student_questions)


def _normalize_timing_fields(data):
    has_time_limit_raw = data.pop("has_time_limit", None)
    end_time_raw = data.pop("end_time", None)

    allow_upsolving = _parse_bool(data.get("allow_upsolving"), default=False)
    if allow_upsolving is None:
        return JsonResponse({"detail": "allow_upsolving must be a boolean"}, status=400)
    data["allow_upsolving"] = bool(allow_upsolving)

    if has_time_limit_raw is None:
        # Legacy mode (older clients may send start_time + duration_minutes only).
        if end_time_raw not in (None, ""):
            start_time = _coerce_datetime(data.get("start_time"))
            end_time = _coerce_datetime(end_time_raw)
            if start_time is None or end_time is None:
                return JsonResponse({"detail": "start_time and end_time must be valid datetimes"}, status=400)
            if end_time <= start_time:
                return JsonResponse({"detail": "end_time must be after start_time"}, status=400)
            duration_minutes = int((end_time - start_time).total_seconds() // 60)
            if duration_minutes <= 0:
                return JsonResponse({"detail": "Contest duration must be at least 1 minute"}, status=400)
            data["start_time"] = start_time.isoformat()
            data["duration_minutes"] = duration_minutes
        return None

    has_time_limit = _parse_bool(has_time_limit_raw, default=None)
    if has_time_limit is None:
        return JsonResponse({"detail": "has_time_limit must be a boolean"}, status=400)

    if not has_time_limit:
        data["start_time"] = ""
        data["duration_minutes"] = ""
        data["allow_upsolving"] = False
        return None

    start_time = _coerce_datetime(data.get("start_time"))
    end_time = _coerce_datetime(end_time_raw)
    if start_time is None or end_time is None:
        return JsonResponse(
            {"detail": "start_time and end_time are required for timed contests"},
            status=400,
        )
    if end_time <= start_time:
        return JsonResponse({"detail": "end_time must be after start_time"}, status=400)

    duration_minutes = int((end_time - start_time).total_seconds() // 60)
    if duration_minutes <= 0:
        return JsonResponse({"detail": "Contest duration must be at least 1 minute"}, status=400)

    data["start_time"] = start_time.isoformat()
    data["duration_minutes"] = duration_minutes
    return None

def _course_is_teacher(course: Course, user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    if course.owner_id == user.id:
        return True
    return course.participants.filter(user=user, role=CourseParticipant.Role.TEACHER).exists()


def _contest_can_edit(contest: Contest, user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff or user.is_superuser:
        return True
    return contest.created_by_id == user.id


def _resolve_updated_timing(contest: Contest, payload: dict):
    has_time_limit_current = bool(contest.start_time and contest.duration_minutes)
    has_time_limit = _parse_bool(payload.get("has_time_limit"), default=has_time_limit_current)
    if has_time_limit is None:
        return None, JsonResponse({"detail": "has_time_limit must be a boolean"}, status=400)

    if not has_time_limit:
        return {
            "start_time": None,
            "duration_minutes": None,
            "allow_upsolving": False,
        }, None

    current_end = contest.get_end_time()
    start_time = (
        _coerce_datetime(payload.get("start_time"))
        if "start_time" in payload
        else contest.start_time
    )
    end_time = (
        _coerce_datetime(payload.get("end_time"))
        if "end_time" in payload
        else current_end
    )
    if start_time is None or end_time is None:
        return (
            None,
            JsonResponse(
                {"detail": "start_time and end_time are required for timed contests"},
                status=400,
            ),
        )
    if end_time <= start_time:
        return None, JsonResponse({"detail": "end_time must be after start_time"}, status=400)

    duration_minutes = int((end_time - start_time).total_seconds() // 60)
    if duration_minutes <= 0:
        return None, JsonResponse({"detail": "Contest duration must be at least 1 minute"}, status=400)

    allow_upsolving = _parse_bool(
        payload.get("allow_upsolving"),
        default=bool(contest.allow_upsolving),
    )
    if allow_upsolving is None:
        return None, JsonResponse({"detail": "allow_upsolving must be a boolean"}, status=400)

    return {
        "start_time": start_time,
        "duration_minutes": duration_minutes,
        "allow_upsolving": bool(allow_upsolving),
    }, None


def _parse_positive_int(value, *, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return -1
    return parsed if parsed > 0 else -1


def _contest_student_ids(contest: Contest) -> list[int]:
    teacher_ids = set(
        CourseParticipant.objects.filter(
            course=contest.course,
            role=CourseParticipant.Role.TEACHER,
        ).values_list("user_id", flat=True)
    )
    if contest.course and contest.course.owner_id:
        teacher_ids.add(contest.course.owner_id)

    if contest.access_type == Contest.AccessType.PRIVATE:
        candidate_ids = set(contest.allowed_participants.values_list("id", flat=True))
    else:
        candidate_ids = set(
            CourseParticipant.objects.filter(
                course=contest.course,
                role=CourseParticipant.Role.STUDENT,
            ).values_list("user_id", flat=True)
        )
        candidate_ids |= set(contest.allowed_participants.values_list("id", flat=True))

    candidate_ids -= teacher_ids
    return sorted(uid for uid in candidate_ids if uid is not None)


def _parse_filter_datetime(value, *, end_of_day: bool = False):
    if value in (None, ""):
        return None, None

    normalized = str(value).strip()
    if not normalized:
        return None, None

    parsed = parse_datetime(normalized)
    if parsed is None:
        parsed_date = parse_date(normalized)
        if parsed_date is None:
            return None, "must be an ISO datetime or date"
        parsed = datetime.combine(parsed_date, time.max if end_of_day else time.min)

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed, None

@login_required
def create_contest(request, course_id):
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(Course.objects.select_related("section", "owner"), pk=course_id)
    if not _course_is_teacher(course, request.user):
        return JsonResponse(
            {"detail": "Only course teachers can create contests for this course"},
            status=403,
        )

    # Frontend posts JSON; HTML form posts x-www-form-urlencoded.
    # Support both, but prefer JSON when present.
    data = None
    content_type = (request.META.get("CONTENT_TYPE") or "").lower()
    if "application/json" in content_type:
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON payload"}, status=400)
        if not isinstance(payload, dict):
            return JsonResponse({"detail": "JSON payload must be an object"}, status=400)
        data = payload
    else:
        data = request.POST

    # The model has defaults for these; the form still treats them as required unless provided.
    if hasattr(data, "lists"):
        data = {key: values[-1] if values else "" for key, values in data.lists()}
    elif hasattr(data, "copy"):
        data = data.copy()
    else:
        data = dict(data)
    timing_error = _normalize_timing_fields(data)
    if timing_error is not None:
        return timing_error
    data.setdefault("status", Contest.Status.GOING)
    data.setdefault("scoring", Contest.Scoring.IOI)
    data.setdefault("registration_type", Contest.Registration.OPEN)
    data.setdefault("allow_notifications", True)
    data.setdefault("allow_student_questions", True)
    if _parse_bool(data.get("allow_notifications"), default=None) is False:
        data["allow_student_questions"] = False

    form = ContestForm(data, course=course)
    if form.is_valid():
        contest = form.save(created_by=request.user, course=course)
        return JsonResponse(
            {
                "id": contest.id,
                "title": contest.title,
                "course": contest.course_id,
                "is_published": contest.is_published,
                "status": contest.status,
                "is_rated": contest.is_rated,
                "scoring": contest.scoring,
                "registration_type": contest.registration_type,
                "allow_notifications": bool(contest.allow_notifications),
                "allow_student_questions": _contest_questions_enabled(contest),
                "created_by_id": contest.created_by_id,
                **_contest_timing_payload(contest, user=request.user, include_submit=True),
            },
            status=201,
        )

    return JsonResponse({"errors": form.errors}, status=400)

def list_contests(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course_id = request.GET.get("course_id")
    try:
        course_filter = int(course_id) if course_id not in (None, "") else None
    except (TypeError, ValueError):
        return JsonResponse({"detail": "course_id must be an integer"}, status=400)

    # Avoid N+1 queries for course/creator fields in the response.
    contests = (
        Contest.objects.select_related("created_by", "course__section", "course__owner")
        .annotate(problems_count=Count("problems", filter=Q(problems__is_published=True), distinct=True))
        .order_by("position", "-created_at")
    )
    if course_filter is not None:
        contests = contests.filter(course_id=course_filter)

    is_admin = bool(request.user.is_staff or request.user.is_superuser)
    is_authenticated = bool(getattr(request.user, "is_authenticated", False))
    teacher_course_ids: set[int] = set()
    if is_authenticated and not is_admin:
        teacher_course_ids |= set(
            Course.objects.filter(owner=request.user).values_list("id", flat=True)
        )
        teacher_course_ids |= set(
            CourseParticipant.objects.filter(
                user=request.user, role=CourseParticipant.Role.TEACHER
            ).values_list("course_id", flat=True)
        )

    visible = []
    for contest in contests:
        if contest.course is None or not contest.is_visible_to(request.user):
            continue
        is_teacher = is_admin or contest.course_id in teacher_course_ids
        if not is_teacher and contest.problems_count == 0:
            continue
        visible.append(
            {
                "id": contest.id,
                "position": contest.position,
                "title": contest.title,
                "description": contest.description,
                "course": contest.course_id,
                "course_title": contest.course.title if contest.course else None,
                "created_by_id": contest.created_by_id,
                "created_by_username": contest.created_by.username if contest.created_by_id else None,
                "is_published": contest.is_published,
                "access_type": contest.access_type,
                "approval_status": contest.approval_status,
                "status": contest.status,
                "is_rated": contest.is_rated,
                "scoring": contest.scoring,
                "registration_type": contest.registration_type,
                "allow_notifications": bool(contest.allow_notifications),
                "allow_student_questions": _contest_questions_enabled(contest),
                "problems_count": contest.problems_count,
                "access_token": contest.access_token
                if contest.access_type == Contest.AccessType.LINK and (is_teacher or is_admin)
                else None,
                **_contest_timing_payload(contest),
            }
        )

    return JsonResponse({"items": visible}, status=200)


@login_required
def delete_contest(request, contest_id):
    if request.method not in {"POST", "DELETE"}:
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner", "created_by"),
        pk=contest_id,
    )

    is_admin = request.user.is_staff or request.user.is_superuser
    # Default rule: only the contest creator can delete.
    # Admin override: staff/superuser can delete any contest.
    if not is_admin and contest.created_by_id != request.user.id:
        return JsonResponse({"detail": "Only contest creator can delete this contest"}, status=403)

    contest.delete()
    return JsonResponse({"success": True, "deleted_id": contest_id}, status=200)


@login_required
def update_contest(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner"),
        pk=contest_id,
    )
    if not _contest_can_edit(contest, request.user):
        return JsonResponse({"detail": "Only contest owner can update this contest"}, status=403)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "JSON payload must be an object"}, status=400)

    timing_values, timing_error = _resolve_updated_timing(contest, payload)
    if timing_error is not None:
        return timing_error

    contest.start_time = timing_values["start_time"]
    contest.duration_minutes = timing_values["duration_minutes"]
    contest.allow_upsolving = timing_values["allow_upsolving"]
    contest.save(update_fields=["start_time", "duration_minutes", "allow_upsolving", "updated_at"])

    return JsonResponse(
        {
            "id": contest.id,
            "title": contest.title,
            "allow_notifications": bool(contest.allow_notifications),
            "allow_student_questions": _contest_questions_enabled(contest),
            **_contest_timing_payload(contest, user=request.user, include_submit=True),
        },
        status=200,
    )


@login_required
def set_contest_questions(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner"),
        pk=contest_id,
    )
    if not contest.is_user_manager(request.user):
        return JsonResponse({"detail": "Only contest teachers can change contest notification settings"}, status=403)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "JSON payload must be an object"}, status=400)

    has_allow_notifications = "allow_notifications" in payload
    has_allow_student_questions = "allow_student_questions" in payload
    if not has_allow_notifications and not has_allow_student_questions:
        return JsonResponse(
            {"detail": "At least one of allow_notifications or allow_student_questions must be provided"},
            status=400,
        )

    allow_notifications = None
    if has_allow_notifications:
        allow_notifications = _parse_bool(payload.get("allow_notifications"), default=None)
        if allow_notifications is None:
            return JsonResponse({"detail": "allow_notifications must be a boolean"}, status=400)

    allow_student_questions = None
    if has_allow_student_questions:
        allow_student_questions = _parse_bool(payload.get("allow_student_questions"), default=None)
        if allow_student_questions is None:
            return JsonResponse({"detail": "allow_student_questions must be a boolean"}, status=400)

    next_allow_notifications = (
        bool(allow_notifications)
        if allow_notifications is not None
        else bool(contest.allow_notifications)
    )
    if not next_allow_notifications:
        next_allow_student_questions = False
    else:
        next_allow_student_questions = (
            bool(allow_student_questions)
            if allow_student_questions is not None
            else bool(contest.allow_student_questions)
        )

    changed_fields = []
    if bool(contest.allow_notifications) != next_allow_notifications:
        contest.allow_notifications = next_allow_notifications
        changed_fields.append("allow_notifications")
    if bool(contest.allow_student_questions) != next_allow_student_questions:
        contest.allow_student_questions = next_allow_student_questions
        changed_fields.append("allow_student_questions")

    if changed_fields:
        contest.save(update_fields=[*changed_fields, "updated_at"])

    return JsonResponse(
        {
            "id": contest.id,
            "allow_notifications": bool(contest.allow_notifications),
            "allow_student_questions": _contest_questions_enabled(contest),
        },
        status=200,
    )

def contest_detail(request, contest_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner")
        .annotate(problems_count=Count("problems", filter=Q(problems__is_published=True), distinct=True))
        .prefetch_related("problems", "allowed_participants"),
        pk=contest_id,
    )
    if not contest.is_visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    is_admin = request.user.is_staff or request.user.is_superuser
    can_manage = bool(_course_is_teacher(contest.course, request.user) or is_admin)
    if not can_manage and contest.problems_count == 0:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    can_edit = bool(_contest_can_edit(contest, request.user))
    allowed_participants = []
    if can_manage:
        allowed_participants = list(
            contest.allowed_participants.values("id", "username")
        )

    can_view_problems = contest.are_problems_visible_to(request.user)
    problems = []
    if can_view_problems:
        problem_links = (
            ContestProblem.objects.filter(contest_id=contest.id, problem__is_published=True)
            .select_related("problem")
            .order_by("position", "id")
        )
        problems = [
            {
                "id": link.problem_id,
                "title": link.problem.title,
                "position": link.position,
                "index": index,
                "label": contest_problem_label(index),
            }
            for index, link in enumerate(problem_links)
        ]
        leaderboards, overall_leaderboard = build_contest_leaderboards(contest)
    else:
        leaderboards, overall_leaderboard = [], {
            "scoring": contest.scoring,
            "problems_count": 0,
            "entries": [],
        }

    return JsonResponse(
        {
            "id": contest.id,
            "title": contest.title,
            "description": contest.description,
            "course": contest.course_id,
            "course_title": contest.course.title if contest.course else None,
            "is_published": contest.is_published,
            "access_type": contest.access_type,
            "access_token": contest.access_token
            if can_manage and contest.access_type == Contest.AccessType.LINK
            else None,
            "approval_status": contest.approval_status,
            "status": contest.status,
            "is_rated": contest.is_rated,
            "scoring": contest.scoring,
            "registration_type": contest.registration_type,
            "allow_notifications": bool(contest.allow_notifications),
            "allow_student_questions": _contest_questions_enabled(contest),
            "problems_count": len(problems),
            "allowed_participants": allowed_participants,
            "problems": problems,
            "leaderboards": leaderboards,
            "overall_leaderboard": overall_leaderboard,
            "can_manage": can_manage,
            "can_edit": can_edit,
            "can_view_problems": can_view_problems,
            "problems_locked_reason": (
                None if can_view_problems else "Задачи откроются после начала контеста."
            ),
            "course_owner_id": contest.course.owner_id,
            **_contest_timing_payload(contest, user=request.user, include_submit=True),
        },
        status=200,
    )


@login_required
def contest_submissions(request, contest_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner").prefetch_related(
            "allowed_participants"
        ),
        pk=contest_id,
    )
    if not contest.is_user_manager(request.user):
        return JsonResponse({"detail": "Only contest teachers can view all submissions"}, status=403)

    page = _parse_positive_int(request.GET.get("page"), default=1)
    if page <= 0:
        return JsonResponse({"detail": "page must be a positive integer"}, status=400)

    page_size = _parse_positive_int(request.GET.get("page_size"), default=20)
    if page_size <= 0:
        return JsonResponse({"detail": "page_size must be a positive integer"}, status=400)
    page_size = min(page_size, 100)

    problem_links = list(
        ContestProblem.objects.filter(contest_id=contest.id, problem__is_published=True)
        .select_related("problem")
        .order_by("position", "id")
    )
    problem_id_set = {link.problem_id for link in problem_links}
    student_ids = _contest_student_ids(contest)

    problem_options = [
        {
            "id": link.problem_id,
            "title": link.problem.title,
            "label": contest_problem_label(index),
        }
        for index, link in enumerate(problem_links)
    ]
    student_options = list(
        User.objects.filter(id__in=student_ids)
        .values("id", "username")
        .order_by("username", "id")
    )
    status_options = [
        {
            "value": value,
            "label": label,
        }
        for value, label in Submission.STATUS_CHOICES
    ]
    filters_payload = {
        "problems": problem_options,
        "students": student_options,
        "statuses": status_options,
    }

    if not problem_id_set or not student_ids:
        return JsonResponse(
            {
                "count": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 1,
                "next": None,
                "previous": page - 1 if page > 1 else None,
                "results": [],
                "filters": filters_payload,
            },
            status=200,
        )

    problem_meta = {
        link.problem_id: {
            "title": link.problem.title,
            "label": contest_problem_label(index),
        }
        for index, link in enumerate(problem_links)
    }

    requested_problem_id = _parse_positive_int(request.GET.get("problem_id"), default=0)
    if requested_problem_id < 0:
        return JsonResponse({"detail": "problem_id must be a positive integer"}, status=400)
    if requested_problem_id and requested_problem_id not in problem_id_set:
        return JsonResponse({"detail": "problem_id is not part of this contest"}, status=400)

    requested_user_id = _parse_positive_int(request.GET.get("user_id"), default=0)
    if requested_user_id < 0:
        return JsonResponse({"detail": "user_id must be a positive integer"}, status=400)
    if requested_user_id and requested_user_id not in student_ids:
        return JsonResponse({"detail": "user_id is not a contest student"}, status=400)

    raw_statuses = request.GET.getlist("status")
    status_filters = []
    for raw in raw_statuses:
        parts = [part.strip() for part in str(raw).split(",")]
        status_filters.extend([part for part in parts if part])

    valid_statuses = {value for value, _ in Submission.STATUS_CHOICES}
    invalid_statuses = sorted({status for status in status_filters if status not in valid_statuses})
    if invalid_statuses:
        return JsonResponse(
            {"detail": "status contains invalid values", "invalid": invalid_statuses},
            status=400,
        )

    search_query = (request.GET.get("q") or "").strip()

    has_file_raw = request.GET.get("has_file")
    has_file_filter = _parse_bool(has_file_raw, default=None)
    if has_file_raw not in (None, "") and has_file_filter is None:
        return JsonResponse({"detail": "has_file must be a boolean"}, status=400)

    submitted_from, submitted_from_error = _parse_filter_datetime(
        request.GET.get("submitted_from"),
        end_of_day=False,
    )
    if submitted_from_error:
        return JsonResponse({"detail": "submitted_from must be a valid ISO datetime/date"}, status=400)

    submitted_to, submitted_to_error = _parse_filter_datetime(
        request.GET.get("submitted_to"),
        end_of_day=True,
    )
    if submitted_to_error:
        return JsonResponse({"detail": "submitted_to must be a valid ISO datetime/date"}, status=400)
    if submitted_from and submitted_to and submitted_to < submitted_from:
        return JsonResponse({"detail": "submitted_to must be greater than or equal to submitted_from"}, status=400)

    submissions_qs = (
        Submission.objects.filter(
            problem_id__in=problem_id_set,
            user_id__in=student_ids,
        )
        .select_related("problem", "user")
        .order_by("-submitted_at", "-id")
    )
    if requested_problem_id:
        submissions_qs = submissions_qs.filter(problem_id=requested_problem_id)
    if requested_user_id:
        submissions_qs = submissions_qs.filter(user_id=requested_user_id)
    if status_filters:
        submissions_qs = submissions_qs.filter(status__in=status_filters)
    if submitted_from is not None:
        submissions_qs = submissions_qs.filter(submitted_at__gte=submitted_from)
    if submitted_to is not None:
        submissions_qs = submissions_qs.filter(submitted_at__lte=submitted_to)
    if has_file_filter is True:
        submissions_qs = submissions_qs.filter(file__isnull=False).exclude(file="")
    elif has_file_filter is False:
        submissions_qs = submissions_qs.filter(Q(file__isnull=True) | Q(file=""))
    if search_query:
        search_q = Q(user__username__icontains=search_query) | Q(problem__title__icontains=search_query)
        if search_query.isdigit():
            search_q |= Q(id=int(search_query))
        submissions_qs = submissions_qs.filter(search_q)

    total = submissions_qs.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    page_rows = list(submissions_qs[offset : offset + page_size])

    results = []
    for submission in page_rows:
        problem_info = problem_meta.get(submission.problem_id, {})
        file_url = submission.file.url if submission.file else None
        file_name = Path(submission.file.name).name if submission.file else None
        is_csv_file = bool(file_name and file_name.lower().endswith(".csv"))
        results.append(
            {
                "id": submission.id,
                "user_id": submission.user_id,
                "username": submission.user.username if submission.user_id else "",
                "problem_id": submission.problem_id,
                "problem_title": problem_info.get("title") or submission.problem.title,
                "problem_label": problem_info.get("label"),
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "status": submission.status,
                "metrics": submission.metrics,
                "score": _primary_metric(submission.metrics),
                "file_url": file_url,
                "file_name": file_name,
                "is_csv_file": is_csv_file,
            }
        )

    has_next = page < total_pages
    has_previous = page > 1
    return JsonResponse(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "next": page + 1 if has_next else None,
            "previous": page - 1 if has_previous else None,
            "results": results,
            "filters": filters_payload,
        },
        status=200,
    )


def _bulk_add_problems(contest: Contest, problem_ids: list[int]) -> dict:
    """
    Add problems to contest preserving order:
    - existing problems stay in place
    - new problems are appended in the provided order
    """
    if not problem_ids:
        return {"added": [], "already_present": []}

    existing = set(
        ContestProblem.objects.filter(contest=contest, problem_id__in=problem_ids)
        .values_list("problem_id", flat=True)
    )
    to_add = [pid for pid in problem_ids if pid not in existing]
    if not to_add:
        return {"added": [], "already_present": sorted(existing)}

    max_pos = (
        ContestProblem.objects.filter(contest=contest)
        .aggregate(Max("position"))
        .get("position__max")
    )
    start = (max_pos + 1) if max_pos is not None else 0
    links = [
        ContestProblem(contest=contest, problem_id=pid, position=start + idx)
        for idx, pid in enumerate(to_add)
    ]
    ContestProblem.objects.bulk_create(links)
    return {"added": to_add, "already_present": sorted(existing)}

@login_required
def set_contest_access(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section"),
        pk=contest_id,
    )
    if contest.course is None:
        return JsonResponse({"detail": "Contest must belong to a course"}, status=400)

    if not _course_is_teacher(contest.course, request.user):
        return JsonResponse(
            {"detail": "Only course teachers can modify this contest"},
            status=403,
        )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    access_type = payload.get("access_type")
    is_published = payload.get("is_published")
    generate_link = payload.get("generate_link", False)

    valid_types = {choice for choice, _ in Contest.AccessType.choices}
    if access_type not in valid_types:
        return JsonResponse({"detail": f"access_type must be one of {sorted(valid_types)}"}, status=400)

    update_fields = []
    if contest.access_type != access_type:
        contest.access_type = access_type
        update_fields.append("access_type")

    if is_published is not None:
        if bool(is_published) and contest.approval_status != Contest.ApprovalStatus.APPROVED:
            return JsonResponse({"detail": "Contest must be approved before publishing"}, status=400)
        contest.is_published = bool(is_published)
        update_fields.append("is_published")

    if access_type == Contest.AccessType.LINK:
        if generate_link or not contest.access_token:
            contest.access_token = uuid.uuid4().hex
            update_fields.append("access_token")
    elif contest.access_token:
        contest.access_token = ""
        update_fields.append("access_token")

    if update_fields:
        contest.save(update_fields=update_fields)

    return JsonResponse(
        {
            "id": contest.id,
            "access_type": contest.access_type,
            "is_published": contest.is_published,
            "access_token": contest.access_token if contest.access_type == Contest.AccessType.LINK else None,
        }
    )

@login_required
def list_pending_contests(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"detail": "Only admins can moderate contests"}, status=403)

    contests = (
        Contest.objects.filter(approval_status=Contest.ApprovalStatus.PENDING)
        .select_related("course", "created_by")
        .annotate(problems_count=Count("problems"))
        .order_by("-created_at")
    )
    items = [
        {
            "id": contest.id,
            "title": contest.title,
            "description": contest.description,
            "course": contest.course_id,
            "course_title": contest.course.title if contest.course else None,
            "creator": contest.created_by.username if contest.created_by else None,
            "is_published": contest.is_published,
            "access_type": contest.access_type,
            "approval_status": contest.approval_status,
            "problems_count": contest.problems_count,
        }
        for contest in contests
    ]
    return JsonResponse({"items": items}, status=200)

@login_required
@transaction.atomic
def moderate_contest(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"detail": "Only admins can moderate contests"}, status=403)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section"),
        pk=contest_id,
    )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    action = payload.get("action")
    publish = bool(payload.get("publish", False))
    valid_actions = {"approve", "reject"}
    if action not in valid_actions:
        return JsonResponse({"detail": "action must be 'approve' or 'reject'"}, status=400)

    if action == "approve":
        contest.approval_status = Contest.ApprovalStatus.APPROVED
        if publish:
            contest.is_published = True
    else:
        contest.approval_status = Contest.ApprovalStatus.REJECTED
        contest.is_published = False

    contest.approved_by = request.user
    contest.approved_at = timezone.now()
    contest.save(
        update_fields=[
            "approval_status",
            "approved_by",
            "approved_at",
            "is_published",
        ]
    )

    return JsonResponse(
        {
            "id": contest.id,
            "approval_status": contest.approval_status,
            "is_published": contest.is_published,
        },
        status=200,
    )

@login_required
def manage_contest_participants(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section"),
        pk=contest_id,
    )
    if contest.course is None:
        return JsonResponse({"detail": "Contest must belong to a course"}, status=400)

    if not _course_is_teacher(contest.course, request.user):
        return JsonResponse(
            {"detail": "Only course teachers can modify this contest"},
            status=403,
        )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    user_ids = payload.get("user_ids")
    action = payload.get("action", "add")

    if not isinstance(user_ids, list) or not user_ids:
        return JsonResponse({"detail": "user_ids must be a non-empty list"}, status=400)
    try:
        user_ids_int = [int(uid) for uid in user_ids]
    except (TypeError, ValueError):
        return JsonResponse({"detail": "user_ids must contain integers"}, status=400)

    users = list(User.objects.filter(id__in=user_ids_int))
    if len(users) != len(set(user_ids_int)):
        return JsonResponse({"detail": "Some users not found"}, status=400)

    if action == "add":
        contest.allowed_participants.add(*users)
    elif action == "remove":
        contest.allowed_participants.remove(*users)
    else:
        return JsonResponse({"detail": "action must be 'add' or 'remove'"}, status=400)

    current = list(contest.allowed_participants.values("id", "username"))
    return JsonResponse({"allowed_participants": current}, status=200)

@login_required
def add_problem_to_contest(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section"),
        pk=contest_id,
    )
    if contest.course is None:
        return JsonResponse({"detail": "Contest must belong to a course"}, status=400)

    if not _course_is_teacher(contest.course, request.user):
        return JsonResponse(
            {"detail": "Only course teachers can modify this contest"},
            status=403,
        )

    try:
        if request.content_type and "application/json" in request.content_type:
            payload = json.loads(request.body or "{}")
            problem_id = payload.get("problem_id")
        else:
            problem_id = request.POST.get("problem_id")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    if problem_id in (None, ""):
        return JsonResponse({"detail": "problem_id is required"}, status=400)

    try:
        problem_id = int(problem_id)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "problem_id must be an integer"}, status=400)

    # Keep backwards compatible single-add endpoint by delegating to bulk add.
    # Return the legacy "problem" object in the response (tests + any older callers rely on it).
    problem = get_object_or_404(Problem, pk=problem_id)
    if not problem.is_published:
        return JsonResponse(
            {"detail": "Problem must be published before adding to contest"},
            status=400,
        )
    result = _bulk_add_problems(contest, [problem_id])
    added = bool(result["added"])
    return JsonResponse(
        {
            "contest": contest.id,
            "problem": {"id": problem.id, "title": problem.title},
            "added": added,
            "added_ids": result["added"],
            "already_present_ids": result["already_present"],
            "problems_count": ContestProblem.objects.filter(contest=contest).count(),
        },
        status=201 if added else 200,
    )


@login_required
def bulk_add_problems_to_contest(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner"),
        pk=contest_id,
    )
    if contest.course is None:
        return JsonResponse({"detail": "Contest must belong to a course"}, status=400)
    if not _course_is_teacher(contest.course, request.user):
        return JsonResponse({"detail": "Only course teachers can modify this contest"}, status=403)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    problem_ids = payload.get("problem_ids") or []
    if not isinstance(problem_ids, list) or not problem_ids:
        return JsonResponse({"detail": "problem_ids must be a non-empty list"}, status=400)
    try:
        problem_ids_int = [int(pid) for pid in problem_ids]
    except (TypeError, ValueError):
        return JsonResponse({"detail": "problem_ids must contain integers"}, status=400)

    problems = list(Problem.objects.filter(id__in=set(problem_ids_int)))
    if len(problems) != len(set(problem_ids_int)):
        found = {p.id for p in problems}
        missing = sorted(set(problem_ids_int) - found)
        return JsonResponse({"detail": "Some problems not found", "missing": missing}, status=400)
    unpublished = sorted(p.id for p in problems if not p.is_published)
    if unpublished:
        return JsonResponse(
            {
                "detail": "Only published problems can be added to a contest",
                "unpublished": unpublished,
            },
            status=400,
        )

    # Preserve caller order.
    result = _bulk_add_problems(contest, problem_ids_int)
    return JsonResponse(
        {
            "contest": contest.id,
            "added_ids": result["added"],
            "already_present_ids": result["already_present"],
            "problems_count": ContestProblem.objects.filter(contest=contest).count(),
        },
        status=200,
    )


@login_required
def reorder_contest_problems(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner"),
        pk=contest_id,
    )
    if contest.course is None:
        return JsonResponse({"detail": "Contest must belong to a course"}, status=400)
    if not _course_is_teacher(contest.course, request.user):
        return JsonResponse({"detail": "Only course teachers can modify this contest"}, status=403)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    problem_ids = payload.get("problem_ids") or []
    if not isinstance(problem_ids, list) or not problem_ids:
        return JsonResponse({"detail": "problem_ids must be a non-empty list"}, status=400)
    try:
        problem_ids_int = [int(pid) for pid in problem_ids]
    except (TypeError, ValueError):
        return JsonResponse({"detail": "problem_ids must contain integers"}, status=400)

    links = list(
        ContestProblem.objects.filter(contest=contest).order_by("position", "id")
    )
    by_pid = {link.problem_id: link for link in links}
    existing_order = [link.problem_id for link in links]

    requested = [pid for pid in problem_ids_int if pid in by_pid]
    if not requested:
        return JsonResponse({"detail": "No provided problem_ids belong to this contest"}, status=400)

    remaining = [pid for pid in existing_order if pid not in set(requested)]
    new_order = requested + remaining

    for idx, pid in enumerate(new_order):
        by_pid[pid].position = idx
    ContestProblem.objects.bulk_update([by_pid[pid] for pid in new_order], ["position"])

    return JsonResponse(
        {"contest": contest.id, "problem_ids": new_order, "problems_count": len(new_order)},
        status=200,
    )


@login_required
@transaction.atomic
def remove_problem_from_contest(request, contest_id):
    if request.method not in {"POST", "DELETE"}:
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner"),
        pk=contest_id,
    )
    if contest.course is None:
        return JsonResponse({"detail": "Contest must belong to a course"}, status=400)
    if not _course_is_teacher(contest.course, request.user):
        return JsonResponse({"detail": "Only course teachers can modify this contest"}, status=403)

    # Accept either {problem_id} or {problem_ids: []} (JSON preferred; form fallback).
    problem_ids = None
    if request.content_type and "application/json" in (request.content_type or "").lower():
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON payload"}, status=400)
        if isinstance(payload, dict):
            if payload.get("problem_ids") is not None:
                problem_ids = payload.get("problem_ids")
            else:
                problem_ids = payload.get("problem_id")
    else:
        if request.POST.getlist("problem_ids"):
            problem_ids = request.POST.getlist("problem_ids")
        else:
            problem_ids = request.POST.get("problem_id")

    if problem_ids in (None, "", []):
        return JsonResponse({"detail": "problem_id or problem_ids is required"}, status=400)

    if isinstance(problem_ids, list):
        try:
            ids = [int(x) for x in problem_ids]
        except (TypeError, ValueError):
            return JsonResponse({"detail": "problem_ids must contain integers"}, status=400)
    else:
        try:
            ids = [int(problem_ids)]
        except (TypeError, ValueError):
            return JsonResponse({"detail": "problem_id must be an integer"}, status=400)

    ids = [pid for pid in ids if pid is not None]
    if not ids:
        return JsonResponse({"detail": "No valid problem ids provided"}, status=400)

    existing = set(
        ContestProblem.objects.filter(contest=contest, problem_id__in=set(ids)).values_list(
            "problem_id", flat=True
        )
    )
    if not existing:
        return JsonResponse({"detail": "No provided problems belong to this contest"}, status=400)

    ContestProblem.objects.filter(contest=contest, problem_id__in=existing).delete()

    # Re-pack positions so they remain contiguous and stable.
    remaining_links = list(
        ContestProblem.objects.filter(contest=contest).order_by("position", "id")
    )
    for idx, link in enumerate(remaining_links):
        link.position = idx
    if remaining_links:
        ContestProblem.objects.bulk_update(remaining_links, ["position"])

    remaining_ids = [link.problem_id for link in remaining_links]
    return JsonResponse(
        {
            "contest": contest.id,
            "removed_ids": sorted(existing),
            "problem_ids": remaining_ids,
            "problems_count": len(remaining_ids),
        },
        status=200,
    )

@login_required
def contest_success(request):
    return JsonResponse({"detail": "success"})
