from __future__ import annotations

import json
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..models import (
    Contest,
    ContestNotification,
    ContestNotificationRecipient,
    CourseParticipant,
)
from ..services.websocket_notifications import broadcast_contest_notification

User = get_user_model()

_MAX_NOTIFICATION_TEXT_LENGTH = 4000
_MAX_LIST_LIMIT = 500
_DEFAULT_LIST_LIMIT = 200


def _notifications_enabled(contest: Contest) -> bool:
    return bool(contest.allow_notifications)


def _questions_enabled(contest: Contest) -> bool:
    return bool(contest.allow_notifications and contest.allow_student_questions)


def _visible_notification_kinds(contest: Contest) -> tuple[str, ...]:
    if not _notifications_enabled(contest):
        return tuple()
    if _questions_enabled(contest):
        return (
            ContestNotification.Kind.ANNOUNCEMENT,
            ContestNotification.Kind.QUESTION,
            ContestNotification.Kind.ANSWER,
        )
    return (ContestNotification.Kind.ANNOUNCEMENT,)


def _parse_positive_int(value, *, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return -1
    return parsed if parsed > 0 else -1


def _read_json_payload(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None, JsonResponse({"detail": "Invalid JSON payload"}, status=400)
    if not isinstance(payload, dict):
        return None, JsonResponse({"detail": "JSON payload must be an object"}, status=400)
    return payload, None


def _normalize_text(raw_text) -> str:
    return str(raw_text or "").strip()


def _parse_user_ids(raw_ids):
    if raw_ids in (None, ""):
        return None
    if not isinstance(raw_ids, list):
        return "recipient_ids must be a list of user ids"

    normalized = []
    for raw in raw_ids:
        try:
            uid = int(raw)
        except (TypeError, ValueError):
            return "recipient_ids must contain integers"
        if uid <= 0:
            return "recipient_ids must contain positive integers"
        normalized.append(uid)
    return sorted(set(normalized))


def _contest_teacher_ids(contest: Contest) -> list[int]:
    teacher_ids = set(
        CourseParticipant.objects.filter(
            course=contest.course,
            role=CourseParticipant.Role.TEACHER,
        ).values_list("user_id", flat=True)
    )
    if contest.course and contest.course.owner_id:
        teacher_ids.add(contest.course.owner_id)
    if contest.created_by_id:
        teacher_ids.add(contest.created_by_id)
    return sorted(uid for uid in teacher_ids if uid is not None)


def _contest_student_ids(contest: Contest) -> list[int]:
    teacher_ids = set(_contest_teacher_ids(contest))
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


def _audience_label(audience: str) -> str:
    if audience == ContestNotification.Audience.ALL_PARTICIPANTS:
        return "Всем участникам"
    if audience == ContestNotification.Audience.SELECTED_PARTICIPANTS:
        return "Выбранным участникам"
    if audience == ContestNotification.Audience.TEACHERS:
        return "Преподавателям"
    if audience == ContestNotification.Audience.QUESTION_AUTHOR:
        return "Автору вопроса"
    return ""


def _serialize_notification(
    notification: ContestNotification,
    *,
    user_id: int,
    can_manage: bool,
    answer_count: int = 0,
):
    links = list(notification.recipient_links.all())
    link_by_user = {link.user_id: link for link in links}
    user_link = link_by_user.get(user_id)
    is_read = True if user_link is None else bool(user_link.is_read)
    recipient_ids = [link.user_id for link in links]
    recipient_usernames = [link.user.username for link in links if link.user_id]

    payload = {
        "id": notification.id,
        "kind": notification.kind,
        "audience": notification.audience,
        "audience_label": _audience_label(notification.audience),
        "text": notification.text,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "author": {
            "id": notification.author_id,
            "username": notification.author.username if notification.author_id else "",
        },
        "parent_id": notification.parent_id,
        "parent_author_id": notification.parent.author_id if notification.parent_id else None,
        "is_read": bool(is_read),
        "recipient_count": len(recipient_ids),
        "answer_count": int(answer_count or 0),
    }
    if can_manage:
        payload["recipient_ids"] = recipient_ids
        payload["recipient_usernames"] = recipient_usernames
    return payload


def _recipient_unread_count_map(contest_id: int, user_ids: list[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    rows = (
        ContestNotificationRecipient.objects.filter(
            notification__contest_id=contest_id,
            user_id__in=user_ids,
            is_read=False,
        )
        .values("user_id")
        .annotate(total=Count("id"))
    )
    return {int(row["user_id"]): int(row["total"]) for row in rows}


def _broadcast_to_users(
    *,
    contest_id: int,
    notification: ContestNotification,
    recipient_ids: list[int],
):
    if not recipient_ids:
        return

    # "Recipient view" is enough for websocket events:
    # managers still get full question data and can answer without extra fields.
    notification_payload = _serialize_notification(
        notification,
        user_id=recipient_ids[0],
        can_manage=False,
        answer_count=0,
    )
    unread_counts = _recipient_unread_count_map(contest_id, recipient_ids)
    broadcast_contest_notification(
        contest_id=contest_id,
        user_ids=recipient_ids,
        notification_payload=notification_payload,
        unread_count_by_user=unread_counts,
    )


@login_required
def contest_notifications(request, contest_id: int):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner").prefetch_related("allowed_participants"),
        pk=contest_id,
    )
    if not contest.is_visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    can_manage = contest.is_user_manager(request.user)
    limit = _parse_positive_int(request.GET.get("limit"), default=_DEFAULT_LIST_LIMIT)
    if limit <= 0:
        return JsonResponse({"detail": "limit must be a positive integer"}, status=400)
    limit = min(limit, _MAX_LIST_LIMIT)

    visible_kinds = _visible_notification_kinds(contest)

    notifications_qs = (
        ContestNotification.objects.filter(contest=contest)
        .filter(kind__in=visible_kinds)
        .select_related("author", "parent__author")
        .prefetch_related("recipient_links__user")
        .order_by("-created_at", "-id")
    )
    if not can_manage:
        notifications_qs = notifications_qs.filter(
            Q(recipient_links__user=request.user) | Q(author=request.user)
        ).distinct()

    notifications = list(notifications_qs[:limit])
    answer_count_by_question = defaultdict(int)
    for item in notifications:
        if item.kind == ContestNotification.Kind.ANSWER and item.parent_id:
            answer_count_by_question[item.parent_id] += 1

    items = [
        _serialize_notification(
            notification,
            user_id=request.user.id,
            can_manage=can_manage,
            answer_count=answer_count_by_question.get(notification.id, 0),
        )
        for notification in notifications
    ]

    unread_count = ContestNotificationRecipient.objects.filter(
        notification__contest=contest,
        notification__kind__in=visible_kinds,
        user=request.user,
        is_read=False,
    ).count()

    participants = []
    if can_manage and _notifications_enabled(contest):
        student_ids = _contest_student_ids(contest)
        participants = list(
            User.objects.filter(id__in=student_ids)
            .values("id", "username")
            .order_by("username", "id")
        )

    return JsonResponse(
        {
            "items": items,
            "unread_count": int(unread_count),
            "participants": participants,
            "can_manage": bool(can_manage),
            "notifications_enabled": _notifications_enabled(contest),
            "questions_enabled": _questions_enabled(contest),
        },
        status=200,
    )


@login_required
@transaction.atomic
def send_contest_notification(request, contest_id: int):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner").prefetch_related("allowed_participants"),
        pk=contest_id,
    )
    if not contest.is_user_manager(request.user):
        return JsonResponse({"detail": "Only contest teachers can send notifications"}, status=403)
    if not _notifications_enabled(contest):
        return JsonResponse({"detail": "Contest notifications are disabled"}, status=403)

    payload, payload_error = _read_json_payload(request)
    if payload_error is not None:
        return payload_error

    text = _normalize_text(payload.get("text"))
    if not text:
        return JsonResponse({"detail": "text is required"}, status=400)
    if len(text) > _MAX_NOTIFICATION_TEXT_LENGTH:
        return JsonResponse(
            {"detail": f"text is too long (max {_MAX_NOTIFICATION_TEXT_LENGTH} chars)"},
            status=400,
        )

    audience_raw = str(payload.get("audience", "all")).strip().lower()
    allowed_audiences = {"all", "selected"}
    if audience_raw not in allowed_audiences:
        return JsonResponse({"detail": "audience must be 'all' or 'selected'"}, status=400)

    student_ids = _contest_student_ids(contest)
    if not student_ids:
        return JsonResponse({"detail": "No contest participants to notify"}, status=400)
    student_ids_set = set(student_ids)

    if audience_raw == "all":
        recipient_ids = student_ids
        audience = ContestNotification.Audience.ALL_PARTICIPANTS
    else:
        parsed_ids = _parse_user_ids(payload.get("recipient_ids"))
        if isinstance(parsed_ids, str):
            return JsonResponse({"detail": parsed_ids}, status=400)
        recipient_ids = parsed_ids or []
        if not recipient_ids:
            return JsonResponse({"detail": "recipient_ids is required for selected audience"}, status=400)
        invalid = sorted(set(recipient_ids) - student_ids_set)
        if invalid:
            return JsonResponse(
                {"detail": "Some recipients are not contest participants", "invalid": invalid},
                status=400,
            )
        audience = ContestNotification.Audience.SELECTED_PARTICIPANTS

    notification = ContestNotification.objects.create(
        contest=contest,
        author=request.user,
        kind=ContestNotification.Kind.ANNOUNCEMENT,
        audience=audience,
        text=text,
    )
    ContestNotificationRecipient.objects.bulk_create(
        [
            ContestNotificationRecipient(
                notification=notification,
                user_id=user_id,
                is_read=False,
            )
            for user_id in recipient_ids
        ],
        ignore_conflicts=True,
    )
    notification.refresh_from_db()
    notification = (
        ContestNotification.objects.select_related("author", "parent__author")
        .prefetch_related("recipient_links__user")
        .get(pk=notification.id)
    )
    _broadcast_to_users(
        contest_id=contest.id,
        notification=notification,
        recipient_ids=recipient_ids,
    )

    return JsonResponse(
        {
            "notification": _serialize_notification(
                notification,
                user_id=request.user.id,
                can_manage=True,
                answer_count=0,
            ),
        },
        status=201,
    )


@login_required
@transaction.atomic
def ask_contest_question(request, contest_id: int):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner").prefetch_related("allowed_participants"),
        pk=contest_id,
    )
    if not contest.is_visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    if contest.is_user_manager(request.user):
        return JsonResponse({"detail": "Teachers should use announcements instead of student questions"}, status=400)
    if not _notifications_enabled(contest):
        return JsonResponse({"detail": "Contest notifications are disabled"}, status=403)
    if not _questions_enabled(contest):
        return JsonResponse({"detail": "Student questions are disabled for this contest"}, status=403)

    payload, payload_error = _read_json_payload(request)
    if payload_error is not None:
        return payload_error

    text = _normalize_text(payload.get("text"))
    if not text:
        return JsonResponse({"detail": "text is required"}, status=400)
    if len(text) > _MAX_NOTIFICATION_TEXT_LENGTH:
        return JsonResponse(
            {"detail": f"text is too long (max {_MAX_NOTIFICATION_TEXT_LENGTH} chars)"},
            status=400,
        )

    recipient_ids = _contest_teacher_ids(contest)
    recipient_ids = [uid for uid in recipient_ids if uid != request.user.id]
    if not recipient_ids:
        return JsonResponse({"detail": "No teachers found for this contest"}, status=400)

    notification = ContestNotification.objects.create(
        contest=contest,
        author=request.user,
        kind=ContestNotification.Kind.QUESTION,
        audience=ContestNotification.Audience.TEACHERS,
        text=text,
    )
    ContestNotificationRecipient.objects.bulk_create(
        [
            ContestNotificationRecipient(
                notification=notification,
                user_id=user_id,
                is_read=False,
            )
            for user_id in recipient_ids
        ],
        ignore_conflicts=True,
    )
    notification.refresh_from_db()
    notification = (
        ContestNotification.objects.select_related("author", "parent__author")
        .prefetch_related("recipient_links__user")
        .get(pk=notification.id)
    )
    _broadcast_to_users(
        contest_id=contest.id,
        notification=notification,
        recipient_ids=recipient_ids,
    )

    return JsonResponse(
        {
            "notification": _serialize_notification(
                notification,
                user_id=request.user.id,
                can_manage=False,
                answer_count=0,
            ),
        },
        status=201,
    )


@login_required
@transaction.atomic
def answer_contest_question(request, contest_id: int, notification_id: int):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner").prefetch_related("allowed_participants"),
        pk=contest_id,
    )
    if not contest.is_user_manager(request.user):
        return JsonResponse({"detail": "Only contest teachers can answer questions"}, status=403)
    if not _notifications_enabled(contest):
        return JsonResponse({"detail": "Contest notifications are disabled"}, status=403)
    if not _questions_enabled(contest):
        return JsonResponse({"detail": "Student questions are disabled for this contest"}, status=403)

    payload, payload_error = _read_json_payload(request)
    if payload_error is not None:
        return payload_error

    text = _normalize_text(payload.get("text"))
    if not text:
        return JsonResponse({"detail": "text is required"}, status=400)
    if len(text) > _MAX_NOTIFICATION_TEXT_LENGTH:
        return JsonResponse(
            {"detail": f"text is too long (max {_MAX_NOTIFICATION_TEXT_LENGTH} chars)"},
            status=400,
        )

    question = get_object_or_404(
        ContestNotification.objects.select_related("author"),
        pk=notification_id,
        contest=contest,
        kind=ContestNotification.Kind.QUESTION,
    )

    answer = ContestNotification.objects.create(
        contest=contest,
        author=request.user,
        kind=ContestNotification.Kind.ANSWER,
        audience=ContestNotification.Audience.QUESTION_AUTHOR,
        text=text,
        parent=question,
    )
    recipient_ids = []
    if question.author_id and question.author_id != request.user.id:
        recipient_ids = [question.author_id]
        ContestNotificationRecipient.objects.create(
            notification=answer,
            user_id=question.author_id,
            is_read=False,
        )

    answer = (
        ContestNotification.objects.select_related("author", "parent__author")
        .prefetch_related("recipient_links__user")
        .get(pk=answer.id)
    )
    _broadcast_to_users(
        contest_id=contest.id,
        notification=answer,
        recipient_ids=recipient_ids,
    )

    return JsonResponse(
        {
            "notification": _serialize_notification(
                answer,
                user_id=request.user.id,
                can_manage=True,
                answer_count=0,
            ),
        },
        status=201,
    )


@login_required
def mark_contest_notifications_read(request, contest_id: int):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section", "course__owner").prefetch_related("allowed_participants"),
        pk=contest_id,
    )
    if not contest.is_visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    payload, payload_error = _read_json_payload(request)
    if payload_error is not None:
        return payload_error

    notification_ids_raw = payload.get("notification_ids")
    notification_ids = None
    if notification_ids_raw is not None:
        parsed = _parse_user_ids(notification_ids_raw)
        if isinstance(parsed, str):
            return JsonResponse({"detail": parsed.replace("recipient_ids", "notification_ids")}, status=400)
        notification_ids = parsed or []

    visible_kinds = _visible_notification_kinds(contest)
    unread_qs = ContestNotificationRecipient.objects.filter(
        notification__contest=contest,
        notification__kind__in=visible_kinds,
        user=request.user,
        is_read=False,
    )
    if notification_ids is not None:
        unread_qs = unread_qs.filter(notification_id__in=notification_ids)

    marked_count = unread_qs.update(is_read=True, read_at=timezone.now())
    unread_count = ContestNotificationRecipient.objects.filter(
        notification__contest=contest,
        notification__kind__in=visible_kinds,
        user=request.user,
        is_read=False,
    ).count()

    return JsonResponse(
        {
            "marked": int(marked_count),
            "unread_count": int(unread_count),
        },
        status=200,
    )
