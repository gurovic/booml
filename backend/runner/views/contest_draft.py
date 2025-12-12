import json
import uuid

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from ..models import Contest, Course, CourseParticipant, Problem
from ..forms.contest_draft import ContestForm

User = get_user_model()

@login_required
def create_contest(request, course_id):
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(Course, pk=course_id)
    is_teacher = course.participants.filter(
        user=request.user,
        role=CourseParticipant.Role.TEACHER,
    ).exists()
    if not is_teacher:
        return JsonResponse({"detail": "Only teachers can create contests for this course"}, status=403)

    form = ContestForm(request.POST, course=course)
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
        Contest.objects.select_related("course")
        .annotate(problems_count=Count("problems"))
        .order_by("-created_at")
    )
    if course_filter is not None:
        contests = contests.filter(course_id=course_filter)

    visible = []
    for contest in contests:
        if contest.course is None or not contest.is_visible_to(request.user):
            continue
        is_teacher = contest.course.participants.filter(
            user=request.user,
            role=CourseParticipant.Role.TEACHER,
        ).exists()
        visible.append(
            {
                "id": contest.id,
                "title": contest.title,
                "description": contest.description,
                "course": contest.course_id,
                "course_title": contest.course.title if contest.course else None,
                "is_published": contest.is_published,
                "access_type": contest.access_type,
                "status": contest.status,
                "is_rated": contest.is_rated,
                "scoring": contest.scoring,
                "registration_type": contest.registration_type,
                "duration_minutes": contest.duration_minutes,
                "start_time": contest.start_time.isoformat() if contest.start_time else None,
                "problems_count": contest.problems_count,
                "access_token": contest.access_token if contest.access_type == Contest.AccessType.LINK and is_teacher else None,
            }
        )

    return JsonResponse({"items": visible}, status=200)

def contest_detail(request, contest_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    contest = get_object_or_404(
        Contest.objects.select_related("course").annotate(problems_count=Count("problems")),
        pk=contest_id,
    )
    if not contest.is_visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    is_teacher = contest.course and contest.course.participants.filter(
        user=request.user,
        role=CourseParticipant.Role.TEACHER,
    ).exists()
    allowed_participants = []
    if is_teacher:
        allowed_participants = list(
            contest.allowed_participants.values("id", "username")
        )

    return JsonResponse(
        {
            "id": contest.id,
            "title": contest.title,
            "description": contest.description,
            "course": contest.course_id,
            "course_title": contest.course.title if contest.course else None,
            "is_published": contest.is_published,
            "access_type": contest.access_type,
            "access_token": contest.access_token if is_teacher and contest.access_type == Contest.AccessType.LINK else None,
            "status": contest.status,
            "is_rated": contest.is_rated,
            "scoring": contest.scoring,
            "registration_type": contest.registration_type,
            "duration_minutes": contest.duration_minutes,
            "start_time": contest.start_time.isoformat() if contest.start_time else None,
            "problems_count": contest.problems_count,
            "allowed_participants": allowed_participants,
        },
        status=200,
    )

def course_detail(request, course_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    course = get_object_or_404(Course.objects.prefetch_related("participants__user"), pk=course_id)
    is_member = course.owner_id == request.user.id or course.participants.filter(user=request.user).exists()
    if not is_member:
        return JsonResponse({"detail": "Forbidden"}, status=403)

    participants = [
        {
            "id": participant.user_id,
            "username": participant.user.username,
            "role": participant.role,
            "is_owner": participant.is_owner,
        }
        for participant in course.participants.all()
    ]

    return JsonResponse(
        {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "participants": participants,
        },
        status=200,
    )

@login_required
def set_contest_access(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(Contest, pk=contest_id)
    if contest.course is None:
        return JsonResponse({"detail": "Contest must belong to a course"}, status=400)

    is_teacher = contest.course.participants.filter(
        user=request.user,
        role=CourseParticipant.Role.TEACHER,
    ).exists()
    if not is_teacher:
        return JsonResponse({"detail": "Only teachers can modify this contest"}, status=403)

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
def manage_contest_participants(request, contest_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(Contest, pk=contest_id)
    if contest.course is None:
        return JsonResponse({"detail": "Contest must belong to a course"}, status=400)

    is_teacher = contest.course.participants.filter(
        user=request.user,
        role=CourseParticipant.Role.TEACHER,
    ).exists()
    if not is_teacher:
        return JsonResponse({"detail": "Only teachers can modify this contest"}, status=403)

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

    contest = get_object_or_404(Contest, pk=contest_id)
    if contest.course is None:
        return JsonResponse({"detail": "Contest must belong to a course"}, status=400)

    is_teacher = contest.course.participants.filter(
        user=request.user,
        role=CourseParticipant.Role.TEACHER,
    ).exists()
    if not is_teacher:
        return JsonResponse({"detail": "Only teachers can modify this contest"}, status=403)

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
