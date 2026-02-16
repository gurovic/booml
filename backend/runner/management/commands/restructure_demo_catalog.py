from __future__ import annotations

import re
from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction

from runner.models import Contest, ContestProblem, Course, CourseParticipant, Problem, Section


_TRAILING_TAGS_RE = re.compile(r"\s*(?:\[[^\]]+\]\s*)+$")
_LEADING_TAGS_RE = re.compile(r"^(?:\[[^\]]+\]\s*)+")


def _strip_square_tags(title: str) -> str:
    """
    Remove bracketed tag blocks that are used as labels in titles.
    We strip:
    - leading blocks: "[Tag] [Tag2] Title" -> "Title"
    - trailing blocks: "Title [Tag] [Tag2]" -> "Title"

    We intentionally do not strip bracketed parts in the middle of a title.
    """
    if not title:
        return title
    s = _LEADING_TAGS_RE.sub("", title).strip()
    s = _TRAILING_TAGS_RE.sub("", s).strip()
    return re.sub(r"\s{2,}", " ", s)


@dataclass(frozen=True)
class RootPlan:
    root_section_title: str
    container_course_title: str
    # contest title -> target course title (under root section)
    contest_to_course: dict[str, str]
    # ensure these courses exist even if empty
    ensure_courses: list[str]


PLANS: list[RootPlan] = [
    RootPlan(
        root_section_title="Олимпиады",
        container_course_title="Олимпиады",
        contest_to_course={
            "ML-блиц финал": "ML-блиц",
            "FAIO 2025 Qualification": "FAIO",
        },
        ensure_courses=["ML-блиц", "FAIO"],
    ),
    RootPlan(
        root_section_title="Тематическое",
        container_course_title="Тематические задачи",
        contest_to_course={
            # Existing demo contests are classic ML; keep them there by default.
            "PCA": "Классический ML",
            "SVM": "Классический ML",
            "kNN": "Классический ML",
            "Decision Tree": "Классический ML",
            "Логистическая регрессия": "Классический ML",
            "Линейная регрессия": "Классический ML",
            "Анализ данных": "Классический ML",
            "Классификация": "Классический ML",
        },
        ensure_courses=["Классический ML", "Deep Learning"],
    ),
]


class Command(BaseCommand):
    help = (
        "Restructure demo catalog into a friendlier hierarchy:\n"
        "- Root 'Олимпиады': courses 'ML-блиц' and 'FAIO' containing their contests.\n"
        "- Root 'Тематическое': courses 'Классический ML' and 'Deep Learning' (demo contests go to Classic ML).\n"
        "Also strips trailing [TAGS] from problem titles for problems used in thematic contests."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (default: dry-run).",
        )

    def handle(self, *args, **options):
        apply = bool(options.get("apply"))
        self.stdout.write(f"restructure_demo_catalog: apply={apply}")

        moved_total = 0
        renamed_total = 0

        for plan in PLANS:
            moved_total += self._apply_plan(plan, apply=apply)

        # After moving contests, strip [tags] from thematic problems.
        renamed_total += self._strip_thematic_problem_tags(apply=apply)

        self.stdout.write(self.style.SUCCESS(f"Done. moved_contests={moved_total} renamed_problems={renamed_total}"))

    def _find_root(self, title: str) -> Section | None:
        return (
            Section.objects.filter(parent__isnull=True, title=title)
            .order_by("id")
            .first()
        )

    def _find_course(self, *, section: Section, title: str) -> Course | None:
        return (
            Course.objects.filter(section=section, title=title)
            .select_related("owner", "section")
            .order_by("id")
            .first()
        )

    def _ensure_course(
        self,
        *,
        section: Section,
        owner_id: int,
        template_course: Course,
        title: str,
        apply: bool,
    ) -> Course | None:
        existing = self._find_course(section=section, title=title)
        if existing:
            return existing

        self.stdout.write(f"  create course '{title}' in section '{section.title}'")
        if not apply:
            return None

        # Copy basic visibility from the legacy container course.
        course = Course(
            title=title,
            description="",
            is_open=template_course.is_open,
            section=section,
            owner_id=owner_id,
        )
        course.full_clean()
        course.save()

        # Copy participants from the template course, but fix owner flag to match the new course owner.
        parts = list(
            CourseParticipant.objects.filter(course=template_course).values(
                "user_id", "role", "is_owner"
            )
        )
        new_parts = [
            CourseParticipant(
                course=course,
                user_id=p["user_id"],
                role=p["role"],
                is_owner=p["user_id"] == course.owner_id,
            )
            for p in parts
        ]
        CourseParticipant.objects.bulk_create(new_parts, ignore_conflicts=True)
        return course

    def _repack_contest_positions(self, course: Course) -> None:
        contests = list(Contest.objects.filter(course=course).order_by("position", "created_at", "id"))
        for idx, c in enumerate(contests):
            c.position = idx
        if contests:
            Contest.objects.bulk_update(contests, ["position"])

    def _apply_plan(self, plan: RootPlan, *, apply: bool) -> int:
        root = self._find_root(plan.root_section_title)
        if not root:
            self.stdout.write(self.style.WARNING(f"SKIP: root section '{plan.root_section_title}' not found"))
            return 0

        container = self._find_course(section=root, title=plan.container_course_title)
        if not container:
            self.stdout.write(
                self.style.WARNING(
                    f"SKIP: container course '{plan.container_course_title}' not found in '{root.title}'"
                )
            )
            return 0

        contests = list(Contest.objects.filter(course=container).order_by("position", "id"))
        self.stdout.write(
            f"ROOT '{root.title}'({root.id}) container '{container.title}'({container.id}): contests={len(contests)}"
        )

        # Ensure target courses exist (even if a contest set is currently empty).
        target_courses: dict[str, Course] = {}
        for title in plan.ensure_courses:
            c = self._ensure_course(
                section=root,
                owner_id=container.owner_id,
                template_course=container,
                title=title,
                apply=apply,
            )
            if c:
                target_courses[title] = c

        moved = 0
        unknown = []

        if not apply:
            for contest in contests:
                target_title = plan.contest_to_course.get(contest.title)
                if not target_title:
                    unknown.append(contest.title)
                    continue
                self.stdout.write(f"  would move contest '{contest.title}' -> course '{target_title}'")
            if unknown:
                self.stdout.write(self.style.WARNING(f"  unknown contests (will remain): {unknown}"))
            self.stdout.write("  would delete container course if empty after moves")
            return 0

        with transaction.atomic():
            for contest in contests:
                target_title = plan.contest_to_course.get(contest.title)
                if not target_title:
                    unknown.append(contest.title)
                    continue

                target = target_courses.get(target_title)
                if not target:
                    target = self._ensure_course(
                        section=root,
                        owner_id=container.owner_id,
                        template_course=container,
                        title=target_title,
                        apply=True,
                    )
                    # apply=True => must exist now
                    assert target is not None
                    target_courses[target_title] = target

                if contest.course_id != target.id:
                    contest.course = target
                    contest.save(update_fields=["course"])
                    moved += 1

            # Repack positions so ordering is deterministic in the new courses.
            for target in target_courses.values():
                self._repack_contest_positions(target)

            remaining = Contest.objects.filter(course=container).count()
            if remaining == 0:
                container.delete()
                self.stdout.write(self.style.SUCCESS(f"  deleted container course {container.id} '{container.title}'"))
            else:
                self.stdout.write(self.style.WARNING(f"  container still has {remaining} contests; not deleted"))

        if unknown:
            self.stdout.write(self.style.WARNING(f"  unknown contests (left in container): {unknown}"))
        self.stdout.write(self.style.SUCCESS(f"  moved contests: {moved}"))
        return moved

    def _strip_thematic_problem_tags(self, *, apply: bool) -> int:
        root = self._find_root("Тематическое")
        if not root:
            return 0

        # Collect all contests under this root section, then all problems inside them.
        course_ids = list(Course.objects.filter(section=root).values_list("id", flat=True))
        contest_ids = list(Contest.objects.filter(course_id__in=course_ids).values_list("id", flat=True))
        problem_ids = list(
            ContestProblem.objects.filter(contest_id__in=contest_ids).values_list("problem_id", flat=True).distinct()
        )
        if not problem_ids:
            return 0

        problems = list(Problem.objects.filter(id__in=problem_ids).order_by("id"))
        changed = []
        for p in problems:
            old = p.title or ""
            new = _strip_square_tags(old)
            if new and new != old:
                changed.append((p, old, new))

        if not changed:
            return 0

        self.stdout.write(f"Thematic problems: stripping [tags] for {len(changed)} problems")
        for p, old, new in changed[:30]:
            self.stdout.write(f"  {p.id}: '{old}' -> '{new}'")
        if len(changed) > 30:
            self.stdout.write(f"  ... and {len(changed) - 30} more")

        if not apply:
            return 0

        with transaction.atomic():
            for p, _, new in changed:
                p.title = new
            Problem.objects.bulk_update([p for p, _, _ in changed], ["title"])
        return len(changed)
