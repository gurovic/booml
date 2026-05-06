import json
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from runner.models import (
    Contest,
    Course,
    Problem,
    ProblemData,
    Profile,
    Report,
    Section,
    Submission,
)


User = get_user_model()


@dataclass(frozen=True)
class FileRef:
    storage: object
    name: str


def _file_ref(file_field) -> FileRef | None:
    name = getattr(file_field, "name", "") or ""
    if not name:
        return None
    storage = getattr(file_field, "storage", None)
    if storage is None:
        return None
    return FileRef(storage=storage, name=name)


def _delete_files(file_refs: list[FileRef]) -> list[dict]:
    failures = []
    seen: set[tuple[int, str]] = set()
    for ref in file_refs:
        key = (id(ref.storage), ref.name)
        if key in seen:
            continue
        seen.add(key)
        try:
            if ref.storage.exists(ref.name):
                ref.storage.delete(ref.name)
        except Exception as exc:
            failures.append({"name": ref.name, "error": str(exc)})
    return failures


def _delete_sections_bottom_up(section_ids: list[int]) -> int:
    remaining = set(section_ids)
    deleted_count = 0
    while remaining:
        rows = list(Section.objects.filter(id__in=remaining).values_list("id", "parent_id"))
        if not rows:
            break
        existing = {section_id for section_id, _ in rows}
        remaining &= existing
        parent_ids = {parent_id for _, parent_id in rows if parent_id in remaining}
        leaves = sorted(remaining - parent_ids)
        if not leaves:
            raise CommandError("Cannot delete load-test sections: cycle or protected subtree detected.")
        deleted, _ = Section.objects.filter(id__in=leaves).delete()
        deleted_count += deleted
        remaining -= set(leaves)
    return deleted_count


class Command(BaseCommand):
    help = "Dry-run or delete all DB rows and files created for a loadtest_<run_id> data set."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", required=True, help="Run id used in loadtest_<run_id> names.")
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Actually delete data. Without this flag the command is a dry-run.",
        )
        parser.add_argument("--json", action="store_true", help="Print only JSON output.")

    def handle(self, *args, **options):
        run_id = str(options["run_id"]).strip()
        if not run_id:
            raise CommandError("--run-id must be non-empty")

        prefix = f"loadtest_{run_id}"
        dry_run = not bool(options["yes"])

        users_qs = User.objects.filter(username__startswith=prefix)
        user_ids = list(users_qs.values_list("id", flat=True))

        problems_qs = Problem.objects.filter(
            Q(title__startswith=prefix) | Q(author_id__in=user_ids)
        ).distinct()
        problem_ids = list(problems_qs.values_list("id", flat=True))

        courses_qs = Course.objects.filter(
            Q(title__startswith=prefix) | Q(owner_id__in=user_ids)
        ).distinct()
        course_ids = list(courses_qs.values_list("id", flat=True))

        contests_qs = Contest.objects.filter(
            Q(title__startswith=prefix)
            | Q(created_by_id__in=user_ids)
            | Q(course_id__in=course_ids)
            | Q(problems__id__in=problem_ids)
        ).distinct()
        contest_ids = list(contests_qs.values_list("id", flat=True))

        submissions_qs = Submission.objects.filter(
            Q(problem_id__in=problem_ids) | Q(user_id__in=user_ids)
        ).distinct()
        submission_ids = list(submissions_qs.values_list("id", flat=True))

        problem_data_qs = ProblemData.objects.filter(problem_id__in=problem_ids)
        problem_data_ids = list(problem_data_qs.values_list("id", flat=True))

        sections_qs = Section.objects.filter(
            Q(title__startswith=prefix) | Q(owner_id__in=user_ids)
        ).distinct()
        section_ids = list(sections_qs.values_list("id", flat=True))

        reports_qs = self._reports_queryset(prefix, problem_ids, submission_ids)
        report_ids = list(reports_qs.values_list("id", flat=True))

        file_refs = []
        for submission in submissions_qs.only("file"):
            ref = _file_ref(submission.file)
            if ref:
                file_refs.append(ref)

        for problem_data in problem_data_qs:
            for field_name in (
                "train_file",
                "test_file",
                "sample_submission_file",
                "answer_file",
            ):
                ref = _file_ref(getattr(problem_data, field_name))
                if ref:
                    file_refs.append(ref)

        for profile in Profile.objects.filter(user_id__in=user_ids).only("avatar"):
            ref = _file_ref(profile.avatar)
            if ref:
                file_refs.append(ref)

        payload = {
            "run_id": run_id,
            "prefix": prefix,
            "dry_run": dry_run,
            "matched": {
                "users": len(user_ids),
                "sections": len(section_ids),
                "courses": len(course_ids),
                "contests": len(contest_ids),
                "problems": len(problem_ids),
                "problem_data": len(problem_data_ids),
                "submissions": len(submission_ids),
                "reports": len(report_ids),
                "files": len({(id(ref.storage), ref.name) for ref in file_refs}),
            },
            "ids_sample": {
                "users": user_ids[:20],
                "sections": section_ids[:20],
                "courses": course_ids[:20],
                "contests": contest_ids[:20],
                "problems": problem_ids[:20],
                "submissions": submission_ids[:20],
                "reports": report_ids[:20],
            },
        }

        if dry_run:
            self._write(payload, json_only=options["json"])
            return

        with transaction.atomic():
            deleted = {}
            deleted["reports"], _ = Report.objects.filter(id__in=report_ids).delete()
            deleted["submissions"], _ = Submission.objects.filter(id__in=submission_ids).delete()
            deleted["problem_data"], _ = ProblemData.objects.filter(id__in=problem_data_ids).delete()
            deleted["contests"], _ = Contest.objects.filter(id__in=contest_ids).delete()
            deleted["problems"], _ = Problem.objects.filter(id__in=problem_ids).delete()
            deleted["courses"], _ = Course.objects.filter(id__in=course_ids).delete()
            deleted["sections"] = _delete_sections_bottom_up(section_ids)
            deleted["users"], _ = User.objects.filter(id__in=user_ids).delete()

        file_failures = _delete_files(file_refs)
        payload["deleted"] = deleted
        payload["file_delete_failures"] = file_failures
        payload["cleanup_ok"] = not file_failures

        self._write(payload, json_only=options["json"])
        if file_failures:
            raise CommandError("Cleanup deleted DB rows, but some files could not be deleted.")

    def _reports_queryset(self, prefix: str, problem_ids: list[int], submission_ids: list[int]):
        base_file_q = Q(file_name__startswith=prefix) | Q(file_name__icontains=prefix)
        if not problem_ids and not submission_ids:
            return Report.objects.filter(base_file_q)
        try:
            return Report.objects.filter(
                base_file_q
                | Q(test_data__problem_id__in=problem_ids)
                | Q(test_data__submission_id__in=submission_ids)
            ).distinct()
        except Exception:
            return Report.objects.filter(base_file_q).distinct()

    def _write(self, payload: dict, *, json_only: bool) -> None:
        output = json.dumps(payload, indent=2, sort_keys=True)
        if json_only:
            self.stdout.write(output)
            return
        title = "BOOML load-test cleanup dry-run:" if payload["dry_run"] else "BOOML load-test cleanup:"
        self.stdout.write(self.style.SUCCESS(title))
        self.stdout.write(output)
