from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import Course, CourseParticipant, Section

User = get_user_model()


@dataclass(slots=True)
class CourseCreateInput:
    title: str
    owner: User
    section: Section
    is_open: bool = False
    description: str = ""
    teachers: Iterable[User] | None = None
    students: Iterable[User] | None = None


def _unique_users(users: Iterable[User]) -> list[User]:
    """Deduplicate user list while preserving order."""
    unique: list[User] = []
    seen_ids = set()
    for user in users:
        if user is None or user.pk is None:
            raise ValueError("All users must be saved before course creation")
        if user.pk in seen_ids:
            continue
        seen_ids.add(user.pk)
        unique.append(user)
    return unique


def create_course(payload: CourseCreateInput) -> Course:
    if payload.owner is None or payload.owner.pk is None:
        raise ValueError("Owner must be a saved user instance")
    if payload.section is None or payload.section.pk is None:
        raise ValueError("Section must be a saved instance")
    if payload.section.owner_id != payload.owner.pk:
        raise ValueError("Only the section owner can create courses inside it")

    teacher_candidates = [payload.owner]
    if payload.teachers:
        teacher_candidates.extend(payload.teachers)
    teachers = _unique_users(teacher_candidates)

    teacher_ids = {user.pk for user in teachers}
    student_users: list[User] = []
    seen_students = set()
    for user in payload.students or []:
        if user is None or user.pk is None:
            raise ValueError("All students must be saved before course creation")
        if user.pk in teacher_ids or user.pk in seen_students:
            continue
        seen_students.add(user.pk)
        student_users.append(user)

    with transaction.atomic():
        course = Course(
            title=payload.title,
            description=payload.description or "",
            is_open=payload.is_open,
            owner=payload.owner,
            section=payload.section,
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
    Добавить пользователей в курс с указанными ролями.
    Приоритет: teacher > student. Owner всегда остаётся teacher+owner (флаг чинится всегда).
    При allow_role_update=False роли не меняются (кроме фикса owner), новые участники всё равно создаются.
    Возвращает dict с созданными/обновлёнными участниками.
    """
    if course.pk is None:
        raise ValueError("Course must be saved before adding participants")

    teacher_users = _unique_users(teachers or [])
    student_users = _unique_users(students or [])

    teacher_ids = {u.pk for u in teacher_users}
    lookup_ids = teacher_ids | {u.pk for u in student_users}

    existing = {
        p.user_id: p
        for p in CourseParticipant.objects.filter(course=course, user_id__in=lookup_ids)
    }

    created: list[CourseParticipant] = []
    updated: list[CourseParticipant] = []

    with transaction.atomic():
        # Teachers first (owner included)
        for user in teacher_users:
            participant = existing.get(user.pk)
            desired_is_owner = user.pk == course.owner_id
            if participant:
                new_role = CourseParticipant.Role.TEACHER
                new_is_owner = participant.is_owner or desired_is_owner

                # Всегда чиним owner-флаг, даже если обновление ролей запрещено.
                if desired_is_owner and not participant.is_owner:
                    participant.role = new_role
                    participant.is_owner = True
                    participant.save(update_fields=["role", "is_owner"])
                    updated.append(participant)
                    continue

                if allow_role_update and (
                    participant.role != new_role or participant.is_owner != new_is_owner
                ):
                    participant.role = new_role
                    participant.is_owner = new_is_owner
                    participant.save(update_fields=["role", "is_owner"])
                    updated.append(participant)
                continue

            participant = CourseParticipant.objects.create(
                course=course,
                user=user,
                role=CourseParticipant.Role.TEACHER,
                is_owner=desired_is_owner,
            )
            created.append(participant)
            existing[user.pk] = participant

        # Students, skip those already teachers/owner
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

            participant = CourseParticipant.objects.create(
                course=course,
                user=user,
                role=CourseParticipant.Role.STUDENT,
                is_owner=False,
            )
            created.append(participant)
            existing[user.pk] = participant

    return {"created": created, "updated": updated}
