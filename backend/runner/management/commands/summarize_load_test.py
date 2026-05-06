import json

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from runner.models import PreValidation, Problem, ProblemData, Report, Submission


User = get_user_model()

_ACTIVE_STATUSES = {
    Submission.STATUS_PENDING,
    Submission.STATUS_RUNNING,
    Submission.STATUS_VALIDATED,
}


def _file_exists(file_field) -> bool:
    if not file_field or not getattr(file_field, "name", ""):
        return False
    try:
        storage = file_field.storage
        return bool(storage.exists(file_field.name))
    except Exception:
        return False


class Command(BaseCommand):
    help = "Summarize DB/file-system state for a loadtest_<run_id> data set."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", required=True, help="Run id used in loadtest_<run_id> names.")
        parser.add_argument("--json", action="store_true", help="Print only JSON output.")

    def handle(self, *args, **options):
        run_id = str(options["run_id"]).strip()
        if not run_id:
            raise ValueError("--run-id must be non-empty")

        prefix = f"loadtest_{run_id}"
        user_ids = list(User.objects.filter(username__startswith=prefix).values_list("id", flat=True))
        problems = list(
            Problem.objects.filter(Q(title__startswith=prefix) | Q(author_id__in=user_ids))
            .distinct()
            .order_by("id")
        )
        problem_ids = [problem.id for problem in problems]

        submissions_qs = Submission.objects.filter(
            Q(problem_id__in=problem_ids) | Q(user_id__in=user_ids)
        ).distinct()
        submission_ids = list(submissions_qs.values_list("id", flat=True))
        status_counts = dict(
            submissions_qs.values("status").annotate(total=Count("id")).values_list("status", "total")
        )

        prevalidation_count = PreValidation.objects.filter(submission_id__in=submission_ids).count()
        submissions_with_prevalidation = set(
            PreValidation.objects.filter(submission_id__in=submission_ids).values_list(
                "submission_id", flat=True
            )
        )
        prevalidation_missing = [
            sid for sid in submission_ids if sid not in submissions_with_prevalidation
        ]

        report_count = 0
        if problem_ids or submission_ids:
            try:
                report_count = Report.objects.filter(
                    Q(test_data__problem_id__in=problem_ids)
                    | Q(test_data__submission_id__in=submission_ids)
                    | Q(file_name__startswith=prefix)
                    | Q(file_name__icontains=prefix)
                ).count()
            except Exception:
                report_count = Report.objects.filter(file_name__icontains=prefix).count()

        missing_submission_files = []
        for submission in submissions_qs.only("id", "file"):
            if not _file_exists(submission.file):
                missing_submission_files.append(submission.id)

        problem_data_rows = list(ProblemData.objects.filter(problem_id__in=problem_ids))
        missing_problem_files = []
        for row in problem_data_rows:
            for field_name in (
                "train_file",
                "test_file",
                "sample_submission_file",
                "answer_file",
            ):
                file_field = getattr(row, field_name)
                if getattr(file_field, "name", "") and not _file_exists(file_field):
                    missing_problem_files.append(
                        {"problem_id": row.problem_id, "field": field_name, "name": file_field.name}
                    )

        active_submission_ids = list(
            submissions_qs.filter(status__in=_ACTIVE_STATUSES)
            .order_by("id")
            .values_list("id", flat=True)
        )

        payload = {
            "run_id": run_id,
            "prefix": prefix,
            "users": {
                "count": len(user_ids),
                "ids_sample": user_ids[:50],
            },
            "problems": {
                "count": len(problems),
                "ids": problem_ids,
                "published": sum(1 for problem in problems if problem.is_published),
            },
            "submissions": {
                "count": len(submission_ids),
                "status_counts": status_counts,
                "active_count": len(active_submission_ids),
                "active_ids_sample": active_submission_ids[:50],
                "missing_file_count": len(missing_submission_files),
                "missing_file_ids_sample": missing_submission_files[:50],
            },
            "prevalidations": {
                "count": prevalidation_count,
                "missing_count": len(prevalidation_missing),
                "missing_submission_ids_sample": prevalidation_missing[:50],
            },
            "reports": {"count": report_count},
            "problem_data": {
                "count": len(problem_data_rows),
                "missing_file_count": len(missing_problem_files),
                "missing_files_sample": missing_problem_files[:50],
            },
            "acceptance": {
                "has_unexpected_missing_submission_files": bool(missing_submission_files),
                "has_missing_prevalidations": bool(prevalidation_missing),
                "has_active_submissions": bool(active_submission_ids),
                "has_missing_problem_files": bool(missing_problem_files),
            },
        }

        output = json.dumps(payload, indent=2, sort_keys=True)
        if options["json"]:
            self.stdout.write(output)
        else:
            self.stdout.write(self.style.SUCCESS("BOOML load-test summary:"))
            self.stdout.write(output)
