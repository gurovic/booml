from django.db.models import Count, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from ..models import Contest, Course, CourseParticipant
from ..services.user_access import is_platform_admin

User = get_user_model()


def _contest_timing_payload(contest: Contest) -> dict:
    end_time = contest.get_end_time()
    return {
        "start_time": contest.start_time.isoformat() if contest.start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "duration_minutes": contest.duration_minutes,
        "has_time_limit": bool(contest.start_time and contest.duration_minutes),
        "allow_upsolving": bool(contest.allow_upsolving),
        "time_state": contest.time_state(),
    }


def _course_is_teacher(course: Course, user) -> bool:
    if not user.is_authenticated:
        return False
    if is_platform_admin(user):
        return True
    if user.is_staff or user.is_superuser:
        return True
    if course.owner_id == user.id:
        return True
    return course.participants.filter(
        user=user, role=CourseParticipant.Role.TEACHER
    ).exists()


def _course_is_member(course: Course, user) -> bool:
    if not user.is_authenticated:
        return False
    if is_platform_admin(user):
        return True
    if user.is_staff or user.is_superuser:
        return True
    if course.owner_id == user.id:
        return True
    return course.participants.filter(user=user).exists()


def course_detail(request, course_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    course = get_object_or_404(
        Course.objects.select_related("section", "owner").prefetch_related("participants__user"),
        pk=course_id,
    )
    is_admin = bool(is_platform_admin(request.user) or request.user.is_staff or request.user.is_superuser)
    is_owner = course.owner_id == request.user.id
    is_teacher = _course_is_teacher(course, request.user)
    is_member = _course_is_member(course, request.user)
    if not (is_admin or is_member or course.is_open):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    participants = []
    if is_admin or is_member:
        participants = [
            {
                "id": participant.user_id,
                "username": participant.user.username,
                "role": participant.role,
                "is_owner": participant.is_owner,
            }
            for participant in course.participants.all()
            if not is_platform_admin(participant.user)
        ]

    return JsonResponse(
        {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "is_open": course.is_open,
            "section": course.section_id,
            "section_title": course.section.title,
            "owner_id": course.owner_id,
            "owner_username": course.owner.username if course.owner_id else None,
            "can_create_contest": bool(is_teacher),
            "can_manage_course": bool(is_owner or is_admin),
            "participants": participants,
        },
        status=200,
    )


def course_contests(request, course_id):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    course = get_object_or_404(
        Course.objects.select_related("section", "owner").prefetch_related("participants__user"),
        pk=course_id,
    )
    is_admin = bool(is_platform_admin(request.user) or request.user.is_staff or request.user.is_superuser)
    is_member = _course_is_member(course, request.user)
    if not (is_admin or is_member or course.is_open):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    contests = (
        Contest.objects.filter(course=course)
        .select_related("course__section", "course__owner", "created_by")
        .annotate(problems_count=Count("problems"))
        .order_by("position", "-created_at")
    )
    is_teacher = _course_is_teacher(course, request.user)
    items = []
    for contest in contests:
        if not contest.is_visible_to(request.user):
            continue
        items.append(
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
                "problems_count": contest.problems_count,
                "access_token": contest.access_token
                if contest.access_type == Contest.AccessType.LINK and (is_teacher or is_admin)
                else None,
                **_contest_timing_payload(contest),
            }
        )
    return JsonResponse({"items": items}, status=200)


@login_required
def reorder_course_contests(request, course_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(
        Course.objects.prefetch_related("participants__user"),
        pk=course_id,
    )
    if not _course_is_teacher(course, request.user):
        return JsonResponse({"detail": "Only course teachers can reorder contests"}, status=403)

    try:
        import json

        payload = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    contest_ids = payload.get("contest_ids") or []
    if not isinstance(contest_ids, list) or not contest_ids:
        return JsonResponse({"detail": "contest_ids must be a non-empty list"}, status=400)
    try:
        contest_ids_int = [int(cid) for cid in contest_ids]
    except (TypeError, ValueError):
        return JsonResponse({"detail": "contest_ids must contain integers"}, status=400)

    contests = list(Contest.objects.filter(course=course).order_by("position", "-created_at", "-id"))
    by_id = {c.id: c for c in contests}
    existing_order = [c.id for c in contests]

    requested = [cid for cid in contest_ids_int if cid in by_id]
    if not requested:
        return JsonResponse({"detail": "No provided contest_ids belong to this course"}, status=400)

    remaining = [cid for cid in existing_order if cid not in set(requested)]
    new_order = requested + remaining
    for idx, cid in enumerate(new_order):
        by_id[cid].position = idx
    Contest.objects.bulk_update([by_id[cid] for cid in new_order], ["position"])

    return JsonResponse({"course_id": course.id, "contest_ids": new_order}, status=200)


@login_required
def update_course(request, course_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(Course, pk=course_id)
    is_admin = bool(is_platform_admin(request.user) or request.user.is_staff or request.user.is_superuser)
    if not (is_admin or course.owner_id == request.user.id):
        return JsonResponse({"detail": "Only course owner can update course"}, status=403)

    try:
        import json
        payload = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    update_fields = []
    if "title" in payload:
        course.title = str(payload.get("title") or "").strip()
        update_fields.append("title")
    if "description" in payload:
        course.description = str(payload.get("description") or "")
        update_fields.append("description")
    if "is_open" in payload:
        course.is_open = bool(payload.get("is_open"))
        update_fields.append("is_open")

    if not update_fields:
        return JsonResponse({"detail": "No fields to update"}, status=400)

    course.save(update_fields=update_fields)
    return JsonResponse(
        {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "is_open": course.is_open,
        },
        status=200,
    )


@login_required
def delete_course(request, course_id):
    if request.method not in {"POST", "DELETE"}:
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(Course, pk=course_id)
    is_admin = bool(is_platform_admin(request.user) or request.user.is_staff or request.user.is_superuser)
    if not (is_admin or course.owner_id == request.user.id):
        return JsonResponse({"detail": "Only course owner can delete course"}, status=403)

    course.delete()
    return JsonResponse({"success": True, "deleted_id": course_id}, status=200)


@login_required
def update_course_participants(request, course_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(Course.objects.prefetch_related("participants__user"), pk=course_id)
    is_admin = bool(is_platform_admin(request.user) or request.user.is_staff or request.user.is_superuser)
    if not (is_admin or course.owner_id == request.user.id):
        return JsonResponse({"detail": "Only course owner can manage participants"}, status=403)

    try:
        import json

        payload = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    teacher_usernames = payload.get("teacher_usernames") or []
    student_usernames = payload.get("student_usernames") or []
    allow_role_update = bool(payload.get("allow_role_update", True))

    if not isinstance(teacher_usernames, list) or not isinstance(student_usernames, list):
        return JsonResponse(
            {"detail": "teacher_usernames and student_usernames must be lists"},
            status=400,
        )

    teacher_usernames = [str(u).strip() for u in teacher_usernames if str(u).strip()]
    student_usernames = [str(u).strip() for u in student_usernames if str(u).strip()]

    users = list(User.objects.filter(username__in=set(teacher_usernames + student_usernames)))
    user_by_username = {u.username: u for u in users}

    missing = sorted(
        {u for u in set(teacher_usernames + student_usernames) if u not in user_by_username}
    )
    if missing:
        return JsonResponse({"detail": "Some users not found", "missing": missing}, status=400)

    from ..services.course_service import add_users_to_course

    result = add_users_to_course(
        course=course,
        teachers=[user_by_username[u] for u in teacher_usernames],
        students=[user_by_username[u] for u in student_usernames],
        allow_role_update=allow_role_update,
    )

    def _summarize(participants):
        return [
            {
                "user_id": p.user_id,
                "username": p.user.username,
                "role": p.role,
                "is_owner": p.is_owner,
            }
            for p in participants
        ]

    return JsonResponse(
        {"course_id": course.id, "created": _summarize(result["created"]), "updated": _summarize(result["updated"])},
        status=200,
    )


@login_required
def remove_course_participants(request, course_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(Course, pk=course_id)
    is_admin = bool(is_platform_admin(request.user) or request.user.is_staff or request.user.is_superuser)
    if not (is_admin or course.owner_id == request.user.id):
        return JsonResponse({"detail": "Only course owner can manage participants"}, status=403)

    try:
        import json

        payload = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"detail": "Invalid JSON payload"}, status=400)

    usernames = payload.get("usernames") or []
    if not isinstance(usernames, list) or not usernames:
        return JsonResponse({"detail": "usernames must be a non-empty list"}, status=400)
    usernames = [str(u).strip() for u in usernames if str(u).strip()]
    users = list(User.objects.filter(username__in=set(usernames)))
    by_name = {u.username: u for u in users}
    missing = sorted({u for u in set(usernames) if u not in by_name})
    if missing:
        return JsonResponse({"detail": "Some users not found", "missing": missing}, status=400)

    if course.owner_id and course.owner.username in set(usernames):
        return JsonResponse({"detail": "Cannot remove course owner"}, status=400)

    deleted, _ = CourseParticipant.objects.filter(course=course, user__in=users).delete()
    return JsonResponse({"course_id": course.id, "removed": usernames, "deleted": deleted}, status=200)
