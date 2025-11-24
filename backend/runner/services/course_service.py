from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

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
    teachers: Iterable[User] | None = None
    students: Iterable[User] | None = None


def _unique_users(users: Iterable[User]) -> List[User]:
    """Deduplicate user list while preserving order."""
    unique: List[User] = []
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

    teacher_candidates = [payload.owner]
    if payload.teachers:
        teacher_candidates.extend(payload.teachers)
    teachers = _unique_users(teacher_candidates)

    teacher_ids = {user.pk for user in teachers}
    student_users: List[User] = []
    seen_students = set()
    for user in payload.students or []:
        if user is None or user.pk is None:
            raise ValueError("All students must be saved before course creation")
        if user.pk in teacher_ids or user.pk in seen_students:
            continue
        seen_students.add(user.pk)
        student_users.append(user)

    with transaction.atomic():
        course = Course.objects.create(
            title=payload.title,
            description=payload.description or "",
            is_open=payload.is_open,
            owner=payload.owner,
        )

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
