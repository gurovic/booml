from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import Section

User = get_user_model()

# Root categories shown on HomePage. Historically they existed under different titles
# ("Тематические" vs "Тематическое", "Авторские" vs "Авторское"), so we treat them as aliases.
ROOT_SECTION_CANONICAL_ORDER = ("Олимпиады", "Тематические", "Авторские")
ROOT_SECTION_TITLE_ALIASES: dict[str, str] = {
    "Олимпиады": "Олимпиады",
    "Тематические": "Тематические",
    "Тематическое": "Тематические",
    "Авторские": "Авторские",
    "Авторское": "Авторские",
}
ROOT_SECTION_TITLES = tuple(ROOT_SECTION_TITLE_ALIASES.keys())


@dataclass(slots=True)
class SectionCreateInput:
    title: str
    owner: User
    description: str = ""
    parent: Section | None = None


def _ensure_no_cycles(parent: Section, child_id: int | None) -> None:
    """Defensive check against circular hierarchies when assigning parent."""
    visited: set[int] = set()
    current = parent
    while current:
        if current.pk:
            if current.pk == child_id:
                raise ValueError("Section cannot be its own ancestor")
            if current.pk in visited:
                raise ValueError("Circular section hierarchy detected")
            visited.add(current.pk)
        current = current.parent


def is_root_section(section: Section) -> bool:
    return section.parent_id is None and section.title in ROOT_SECTION_TITLE_ALIASES


def root_section_order_key(section: Section) -> tuple[int, str]:
    """Stable ordering for root categories across title aliases."""
    canonical = ROOT_SECTION_TITLE_ALIASES.get(section.title)
    try:
        idx = ROOT_SECTION_CANONICAL_ORDER.index(canonical) if canonical else 10_000
    except ValueError:
        idx = 10_000
    return (idx, (section.title or "").lower())


def create_section(payload: SectionCreateInput) -> Section:
    if payload.owner is None or payload.owner.pk is None:
        raise ValueError("Owner must be a saved user instance")
    if payload.parent is not None and payload.parent.pk is None:
        raise ValueError("Parent section must be saved before use")
    if payload.parent is None and payload.title not in ROOT_SECTION_TITLES:
        raise ValueError("Root sections must be one of the predefined categories")
    if payload.parent is not None:
        if not is_root_section(payload.parent) and payload.parent.owner_id != payload.owner.pk:
            raise ValueError("Only section owner can create nested sections")
        _ensure_no_cycles(payload.parent, child_id=None)
    if payload.parent is None and Section.objects.filter(
        parent__isnull=True, title=payload.title
    ).exists():
        raise ValueError("Root section already exists")

    with transaction.atomic():
        section = Section(
            title=payload.title,
            description=payload.description or "",
            owner=payload.owner,
            parent=payload.parent,
        )
        section.full_clean()
        section.save()

    return section
