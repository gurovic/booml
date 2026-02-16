from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction

from runner.models import Contest, Course, CourseParticipant, Section


@dataclass(frozen=True)
class ContainerSpec:
    root_section_title: str
    container_course_title: str


SPECS: list[ContainerSpec] = [
    ContainerSpec(root_section_title="Олимпиады", container_course_title="Олимпиады"),
    ContainerSpec(
        root_section_title="Тематическое", container_course_title="Тематические задачи"
    ),
]


class Command(BaseCommand):
    help = (
        "Flatten legacy 'container' courses inside root sections by moving their contests "
        "into newly created courses directly under the root section. "
        "This removes an extra nesting level on the Home page."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (default: dry-run).",
        )

    def handle(self, *args, **options):
        apply = bool(options.get("apply"))
        self.stdout.write(f"flatten_root_containers: apply={apply}")

        for spec in SPECS:
            self._process_spec(spec, apply=apply)

    def _process_spec(self, spec: ContainerSpec, *, apply: bool) -> None:
        root = (
            Section.objects.filter(parent__isnull=True, title=spec.root_section_title)
            .order_by("id")
            .first()
        )
        if not root:
            self.stdout.write(
                self.style.WARNING(
                    f"SKIP: root section '{spec.root_section_title}' not found"
                )
            )
            return

        container = (
            Course.objects.filter(section=root, title=spec.container_course_title)
            .select_related("owner", "section")
            .order_by("id")
            .first()
        )
        if not container:
            self.stdout.write(
                self.style.WARNING(
                    f"SKIP: container course '{spec.container_course_title}' not found in '{root.title}'"
                )
            )
            return

        contests = list(Contest.objects.filter(course=container).order_by("position", "id"))
        if not contests:
            self.stdout.write(
                self.style.WARNING(
                    f"SKIP: container course '{container.title}' has no contests"
                )
            )
            return

        participants = list(
            CourseParticipant.objects.filter(course=container).values(
                "user_id", "role", "is_owner"
            )
        )

        self.stdout.write(
            f"ROOT '{root.title}'({root.id}) container course '{container.title}'({container.id}): "
            f"{len(contests)} contests"
        )

        if not apply:
            for c in contests:
                self.stdout.write(f"  would move contest {c.id} '{c.title}'")
            self.stdout.write("  would delete container course if empty after move")
            return

        with transaction.atomic():
            moved = 0
            created_courses = 0

            for contest in contests:
                target = (
                    Course.objects.filter(
                        section=root, owner=container.owner, title=contest.title
                    )
                    .exclude(id=container.id)
                    .order_by("id")
                    .first()
                )

                if not target:
                    target = Course(
                        title=contest.title,
                        description=contest.description or "",
                        is_open=container.is_open,
                        section=root,
                        owner=container.owner,
                    )
                    target.full_clean()
                    target.save()
                    created_courses += 1

                # Copy participants from the container course.
                # Owner flag is derived from the new course owner.
                new_parts = [
                    CourseParticipant(
                        course=target,
                        user_id=p["user_id"],
                        role=p["role"],
                        is_owner=p["user_id"] == target.owner_id,
                    )
                    for p in participants
                ]
                CourseParticipant.objects.bulk_create(new_parts, ignore_conflicts=True)

                contest.course = target
                contest.save(update_fields=["course"])
                moved += 1

            remaining = Contest.objects.filter(course=container).count()
            if remaining == 0:
                container.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  deleted container course {container.id} '{container.title}'"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  container course still has {remaining} contests; not deleted"
                    )
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  moved {moved} contests; created {created_courses} courses under '{root.title}'"
                )
            )

