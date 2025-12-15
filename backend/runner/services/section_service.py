from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from django.contrib.auth import get_user_model

from ..models import Contest, Course, Problem, Section

User = get_user_model()


def _pick_section_owner(preferred: User | None = None) -> User:
    """
    Select an owner for system/root sections.
    Priority: preferred user -> superuser -> staff -> first user.
    Creates a dedicated system user if nothing exists.
    """
    if preferred and preferred.is_authenticated:
        return preferred

    owner = (
        User.objects.filter(is_superuser=True).first()
        or User.objects.filter(is_staff=True).first()
        or User.objects.order_by("id").first()
    )
    if owner:
        return owner

    # Fallback: create a system user with unusable password.
    system_user = User.objects.create_user(username="system_root_sections")
    system_user.set_unusable_password()
    system_user.save(update_fields=["password"])
    return system_user


def ensure_root_sections(preferred_owner: User | None = None) -> list[Section]:
    """
    Make sure three root sections exist. They are shared and owned by a consistent user.
    """
    owner = _pick_section_owner(preferred_owner)
    roots: list[Section] = []
    for title in Section.ROOT_TITLES:
        section = Section.objects.filter(title=title, parent=None).first()
        if section is None:
            section = Section(
                title=title,
                parent=None,
                owner=owner,
                description="",
                is_public=True,
            )
            section.full_clean()
            section.save()
        roots.append(section)
    return roots


def build_section_tree(
    sections: Iterable[Section] | None = None,
    courses: Iterable[Course] | None = None,
    contests: Iterable[Contest] | None = None,
) -> list[dict]:
    """
    Return a nested tree with sections -> courses -> contests -> problems.
    """
    sections = list(sections) if sections is not None else list(
        Section.objects.all().select_related("parent").order_by("title")
    )
    courses = list(courses) if courses is not None else list(
        Course.objects.select_related("section").order_by("title")
    )
    contests = list(contests) if contests is not None else list(
        Contest.objects.select_related("course").prefetch_related("problems").order_by("title")
    )

    section_children: dict[int | None, list[Section]] = defaultdict(list)
    for section in sections:
        section_children[section.parent_id].append(section)

    courses_by_section: dict[int, list[Course]] = defaultdict(list)
    for course in courses:
        if course.section_id is None:
            continue
        courses_by_section[course.section_id].append(course)

    contests_by_course: dict[int, list[Contest]] = defaultdict(list)
    for contest in contests:
        if contest.course_id is None:
            continue
        contests_by_course[contest.course_id].append(contest)

    def serialize_contest(contest: Contest) -> dict:
        problems: list[Problem] = sorted(contest.problems.all(), key=lambda p: p.title)
        return {
            "id": contest.id,
            "title": contest.title,
            "type": "contest",
            "is_published": contest.is_published,
            "status": contest.status,
            "problem_ids": [problem.id for problem in problems],
            "problem_count": len(problems),
            "problems": [
                {"id": problem.id, "title": problem.title, "type": "problem"}
                for problem in problems
            ],
        }

    def serialize_course(course: Course) -> dict:
        course_contests = contests_by_course.get(course.id, [])
        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "type": "course",
            "is_open": course.is_open,
            "contest_count": len(course_contests),
            "contests": [serialize_contest(contest) for contest in course_contests],
        }

    def serialize_section(section: Section) -> dict:
        children = []
        for child_section in sorted(section_children.get(section.id, []), key=lambda s: s.title):
            children.append(serialize_section(child_section))
        for course in sorted(courses_by_section.get(section.id, []), key=lambda c: c.title):
            children.append(serialize_course(course))

        return {
            "id": section.id,
            "title": section.title,
            "description": section.description,
            "type": "section",
            "children": children,
        }

    root_candidates = section_children.get(None, [])
    ordered_roots: list[Section] = []
    for title in Section.ROOT_TITLES:
        ordered_roots.extend([s for s in root_candidates if s.title == title])
    for section in root_candidates:
        if section not in ordered_roots:
            ordered_roots.append(section)

    return [serialize_section(section) for section in ordered_roots]
