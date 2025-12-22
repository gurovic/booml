from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ..models import Contest, Course, CourseParticipant


def course_detail(request, course_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    course = get_object_or_404(Course.objects.prefetch_related("participants__user"), pk=course_id)
    is_admin = request.user.is_staff or request.user.is_superuser
    is_member = course.owner_id == request.user.id or course.participants.filter(user=request.user).exists()
    if not (is_member or is_admin):
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


def course_contests(request, course_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    course = get_object_or_404(Course.objects.prefetch_related("participants__user"), pk=course_id)
    is_admin = request.user.is_staff or request.user.is_superuser
    is_member = course.owner_id == request.user.id or course.participants.filter(user=request.user).exists()
    if not (is_member or is_admin):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    contests = (
        Contest.objects.filter(course=course)
        .select_related("course")
        .annotate(problems_count=Count("problems"))
        .order_by("-created_at")
    )
    items = []
    for contest in contests:
        if not contest.is_visible_to(request.user):
            continue
        is_teacher = contest.course.participants.filter(
            user=request.user,
            role=CourseParticipant.Role.TEACHER,
        ).exists()
        items.append(
            {
                "id": contest.id,
                "title": contest.title,
                "description": contest.description,
                "course": contest.course_id,
                "course_title": contest.course.title if contest.course else None,
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
    return JsonResponse({"items": items}, status=200)
