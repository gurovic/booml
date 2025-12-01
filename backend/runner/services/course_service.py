from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import Course, CourseParticipant

User = get_user_model()


@dataclass(slots=True)
class CourseCreateInput:
    title: str
    owner: User
    is_open: bool = False
    description: str = ""
    parent: Course | None = None
    teachers: Iterable[User] | None = None
    students: Iterable[User] | None = None


def _unique_users(users: Iterable[User]) -> list[User]:
    unique: list[User] = []
    seen_ids = set()
    for user in users:
        if user is None or user.pk is None:
            raise ValueError("All users must be saved before use")
        if user.pk in seen_ids:
            continue
        seen_ids.add(user.pk)
        unique.append(user)
    return unique


def create_course(payload: CourseCreateInput) -> Course:
    if payload.owner is None or payload.owner.pk is None:
        raise ValueError("Owner must be a saved and persisted user.")
    if payload.parent is not None and payload.parent.pk is None:
        raise ValueError("Parent course must be saved before assignment.")

    teacher_candidates = [payload.owner]
    if payload.teachers:
        teacher_candidates.extend(payload.teachers)
    teachers = _unique_users(teacher_candidates)

    student_users = _unique_users(payload.students or [])
    teacher_ids = {user.pk for user in teachers}
    student_users = [user for user in student_users if user.pk not in teacher_ids]

    with transaction.atomic():
        course = Course(
            title=payload.title,
            description=payload.description or "",
            is_open=payload.is_open,
            owner=payload.owner,
            parent=payload.parent,
        )
        course.full_clean()
        course.save()

        participants = [
            CourseParticipant(
                course=course,
                user=user,
                role=CourseParticipant.Role.TEACHER,
                is_owner=user.pk == payload.owner.pk,
            )
            for user in teachers
        ]
        participants.extend(
            CourseParticipant(
                course=course,
                user=user,
                role=CourseParticipant.Role.STUDENT,
                is_owner=False,
            )
            for user in student_users
        )

        CourseParticipant.objects.bulk_create(participants)

    return course


def add_users_to_course(
    course: Course,
    *,
    teachers: Iterable[User] | None = None,
    students: Iterable[User] | None = None,
    allow_role_update: bool = True,
) -> dict[str, list[CourseParticipant]]:
    """
    Add users to the course with explicit roles.
    Teachers are prioritized over students. Owner always remains teacher+owner.
    When allow_role_update is False, existing roles are not changed except for
    fixing the owner flag. Newly added users are still persisted.
    Returns created/updated participants for auditing.
    """
    if course.pk is None:
        raise ValueError("Course must be persisted before adding participants.")

    teacher_users = _unique_users(teachers or [])
    student_users = _unique_users(students or [])

    teacher_ids = {user.pk for user in teacher_users}
    student_ids = {user.pk for user in student_users}

    lookup_ids = teacher_ids | student_ids
    existing = {
        participant.user_id: participant
        for participant in CourseParticipant.objects.filter(
            course=course, user_id__in=lookup_ids
        )
    }

    created_ids: set[int] = set()
    new_participants: list[CourseParticipant] = []
    updated: list[CourseParticipant] = []

    for user in teacher_users:
        participant = existing.get(user.pk)
        desired_is_owner = user.pk == course.owner_id
        if participant:
            if desired_is_owner and not participant.is_owner:
                participant.role = CourseParticipant.Role.TEACHER
                participant.is_owner = True
                participant.save(update_fields=["role", "is_owner"])
                updated.append(participant)
                continue

            if allow_role_update:
                new_role = CourseParticipant.Role.TEACHER
                if participant.role != new_role or participant.is_owner != desired_is_owner:
                    participant.role = new_role
                    participant.is_owner = desired_is_owner or participant.is_owner
                    participant.save(update_fields=["role", "is_owner"])
                    updated.append(participant)
            continue

        new_participants.append(
            CourseParticipant(
                course=course,
                user=user,
                role=CourseParticipant.Role.TEACHER,
                is_owner=desired_is_owner,
            )
        )
        created_ids.add(user.pk)
        existing[user.pk] = None  # placeholder

    for user in student_users:
        if user.pk in teacher_ids or user.pk == course.owner_id:
            continue

        participant = existing.get(user.pk)
        if participant:
            if participant.role == CourseParticipant.Role.STUDENT:
                continue
            if allow_role_update:
                participant.role = CourseParticipant.Role.STUDENT
                participant.is_owner = False
                participant.save(update_fields=["role", "is_owner"])
                updated.append(participant)
            continue

        new_participants.append(
            CourseParticipant(
                course=course,
                user=user,
                role=CourseParticipant.Role.STUDENT,
                is_owner=False,
            )
        )
        created_ids.add(user.pk)
        existing[user.pk] = None

    if new_participants:
        CourseParticipant.objects.bulk_create(new_participants)
    created = list(
        CourseParticipant.objects.filter(course=course, user_id__in=created_ids)
    )

    return {"created": created, "updated": updated}
