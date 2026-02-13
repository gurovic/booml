import json
import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from ..models import Contest, Course, Problem, CourseParticipant, ContestProblem
from ..forms.contest_draft import ContestForm
from ..services.contest_labels import contest_problem_label
from .contest_leaderboard import build_contest_leaderboards

User = get_user_model()

def _course_is_teacher(course: Course, user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    if course.owner_id == user.id:
        return True
    return course.participants.filter(user=user, role=CourseParticipant.Role.TEACHER).exists()

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
    data = dict(data) if not hasattr(data, "copy") else data.copy()
    data.setdefault("status", Contest.Status.GOING)
    data.setdefault("scoring", Contest.Scoring.IOI)
    data.setdefault("registration_type", Contest.Registration.OPEN)

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
                "duration_minutes": contest.duration_minutes,
                "created_by_id": contest.created_by_id,
            },
            status=201,
        )

    return JsonResponse({"errors": form.errors}, status=400)

def list_contests(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    course_id = request.GET.get("course_id")
    try:
        course_filter = int(course_id) if course_id not in (None, "") else None
    except (TypeError, ValueError):
        return JsonResponse({"detail": "course_id must be an integer"}, status=400)

    # Avoid N+1 queries for course/creator fields in the response.
    contests = (
        Contest.objects.select_related("created_by", "course__section", "course__owner")
        .annotate(problems_count=Count("problems"))
        .order_by("position", "-created_at")
    )
    if course_filter is not None:
        contests = contests.filter(course_id=course_filter)

    is_admin = request.user.is_staff or request.user.is_superuser
    teacher_course_ids: set[int] = set()
    if not is_admin:
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
                "duration_minutes": contest.duration_minutes,
                "start_time": contest.start_time.isoformat() if contest.start_time else None,
                "problems_count": contest.problems_count,
                "access_token": contest.access_token
                if contest.access_type == Contest.AccessType.LINK and (is_teacher or is_admin)
                else None,
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

def contest_detail(request, contest_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner")
        .annotate(problems_count=Count("problems"))
        .prefetch_related("problems", "allowed_participants"),
        pk=contest_id,
    )
    if not contest.is_visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    is_admin = request.user.is_staff or request.user.is_superuser
    can_manage = bool(_course_is_teacher(contest.course, request.user) or is_admin)
    allowed_participants = []
    if can_manage:
        allowed_participants = list(
            contest.allowed_participants.values("id", "username")
        )

    problem_links = (
        ContestProblem.objects.filter(contest_id=contest.id)
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
            "duration_minutes": contest.duration_minutes,
            "start_time": contest.start_time.isoformat() if contest.start_time else None,
            "problems_count": contest.problems_count,
            "allowed_participants": allowed_participants,
            "problems": problems,
            "leaderboards": leaderboards,
            "overall_leaderboard": overall_leaderboard,
            "can_manage": can_manage,
            "course_owner_id": contest.course.owner_id,
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
