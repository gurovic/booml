import json
import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from ..models import Contest, Course, Problem
from ..forms.contest_draft import ContestForm
from .contest_leaderboard import build_contest_leaderboards

User = get_user_model()

@login_required
def create_contest(request, course_id):
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(Course.objects.select_related("section"), pk=course_id)
    if course.section.owner_id != request.user.id:
        return JsonResponse(
            {"detail": "Only section owner can create contests for this course"},
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

    contests = (
        Contest.objects.select_related("course__section")
        .annotate(problems_count=Count("problems"))
        .order_by("-created_at")
    )
    if course_filter is not None:
        contests = contests.filter(course_id=course_filter)

    visible = []
    for contest in contests:
        if contest.course is None or not contest.is_visible_to(request.user):
            continue
        is_owner = contest.course.section.owner_id == request.user.id
        is_admin = request.user.is_staff or request.user.is_superuser
        visible.append(
            {
                "id": contest.id,
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
                if contest.access_type == Contest.AccessType.LINK and (is_owner or is_admin)
                else None,
            }
        )

    return JsonResponse({"items": visible}, status=200)


@login_required
def delete_contest(request, contest_id):
    if request.method not in {"POST", "DELETE"}:
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section"),
        pk=contest_id,
    )

    # Only the teacher who created the contest can delete it.
    if contest.created_by_id != request.user.id:
        return JsonResponse({"detail": "Only contest creator can delete this contest"}, status=403)

    contest.delete()
    return JsonResponse({"success": True, "deleted_id": contest_id}, status=200)

def contest_detail(request, contest_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section")
        .annotate(problems_count=Count("problems"))
        .prefetch_related("problems", "allowed_participants"),
        pk=contest_id,
    )
    if not contest.is_visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    is_owner = contest.course.section.owner_id == request.user.id
    is_admin = request.user.is_staff or request.user.is_superuser
    allowed_participants = []
    if is_owner or is_admin:
        allowed_participants = list(
            contest.allowed_participants.values("id", "username")
        )

    problems = [
        {
            "id": problem.id,
            "title": problem.title,
        }
        for problem in contest.problems.all()
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
            if (is_owner or is_admin) and contest.access_type == Contest.AccessType.LINK
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
            "is_owner": is_owner,
            "section_owner_id": contest.course.section.owner_id,
        },
        status=200,
    )

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

    if contest.course.section.owner_id != request.user.id:
        return JsonResponse(
            {"detail": "Only section owner can modify this contest"},
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

    if contest.course.section.owner_id != request.user.id:
        return JsonResponse(
            {"detail": "Only section owner can modify this contest"},
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

    if contest.course.section.owner_id != request.user.id:
        return JsonResponse(
            {"detail": "Only section owner can modify this contest"},
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

    problem = get_object_or_404(Problem, pk=problem_id)
    already_attached = contest.problems.filter(pk=problem.pk).exists()
    contest.problems.add(problem)

    return JsonResponse(
        {
            "contest": contest.id,
            "problem": {
                "id": problem.id,
                "title": problem.title,
            },
            "added": not already_attached,
            "problems_count": contest.problems.count(),
        },
        status=201 if not already_attached else 200,
    )

@login_required
def contest_success(request):
    return JsonResponse({"detail": "success"})
