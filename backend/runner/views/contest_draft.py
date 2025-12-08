import json

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from ..models import Contest, Course, CourseParticipant, Problem
from ..forms.contest_draft import ContestForm

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
        visible.append(
            {
                "id": contest.id,
                "title": contest.title,
                "description": contest.description,
                "course": contest.course_id,
                "course_title": contest.course.title if contest.course else None,
                "is_published": contest.is_published,
                "status": contest.status,
                "is_rated": contest.is_rated,
                "scoring": contest.scoring,
                "registration_type": contest.registration_type,
                "duration_minutes": contest.duration_minutes,
                "start_time": contest.start_time.isoformat() if contest.start_time else None,
                "problems_count": contest.problems_count,
            }
        )

    return JsonResponse({"items": visible}, status=200)

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
