import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from runner.models import (
    Contest,
    ContestProblem,
    Course,
    CourseParticipant,
    Problem,
    ProblemData,
    ProblemDescriptor,
    Section,
)


User = get_user_model()


def _csv_bytes(rows: int, *, column: str = "prediction") -> bytes:
    lines = [f"id,{column}\n"]
    for idx in range(1, rows + 1):
        value = (idx % 1000) / 1000
        lines.append(f"{idx},{value:.6f}\n")
    return "".join(lines).encode("utf-8")


def _save_problem_files(problem: Problem, *, rows: int, column: str) -> ProblemData:
    answer = ContentFile(_csv_bytes(rows, column=column), name=f"{problem.id}_answer.csv")
    sample = ContentFile(_csv_bytes(rows, column=column), name=f"{problem.id}_sample.csv")
    train = ContentFile(_csv_bytes(min(rows, 1000), column=column), name=f"{problem.id}_train.csv")
    test = ContentFile(_csv_bytes(min(rows, 1000), column=column), name=f"{problem.id}_test.csv")

    problem_data, _ = ProblemData.objects.get_or_create(problem=problem)
    problem_data.answer_file = answer
    problem_data.sample_submission_file = sample
    problem_data.train_file = train
    problem_data.test_file = test
    problem_data.save()
    return problem_data


class Command(BaseCommand):
    help = "Seed isolated BOOML load-test users, problems, descriptors, files, and optional contest."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", required=True, help="Run id used in loadtest_<run_id> names.")
        parser.add_argument("--users", type=int, default=10, help="Number of student users to create.")
        parser.add_argument("--password", default="LoadTestPass123!", help="Password for all seeded users.")
        parser.add_argument(
            "--answer-rows",
            type=int,
            default=1000,
            help="Rows in answer/sample CSV. Match this with load-test --csv-rows for accepted fast checks.",
        )
        parser.add_argument(
            "--create-contest",
            action="store_true",
            help="Also create an approved published contest containing seeded problems.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print only JSON output.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        run_id = str(options["run_id"]).strip()
        if not run_id:
            raise ValueError("--run-id must be non-empty")

        users_count = max(int(options["users"]), 1)
        rows = max(int(options["answer_rows"]), 1)
        password = options["password"]
        prefix = f"loadtest_{run_id}"

        teacher, _ = User.objects.get_or_create(
            username=f"{prefix}_teacher",
            defaults={"email": f"{prefix}_teacher@example.test", "is_staff": True},
        )
        teacher.email = f"{prefix}_teacher@example.test"
        teacher.is_staff = True
        teacher.set_password(password)
        teacher.save()

        students = []
        for idx in range(users_count):
            user, _ = User.objects.get_or_create(
                username=f"{prefix}_student_{idx}",
                defaults={"email": f"{prefix}_student_{idx}@example.test"},
            )
            user.email = f"{prefix}_student_{idx}@example.test"
            user.is_staff = False
            user.set_password(password)
            user.save()
            students.append(user)

        section, _ = Section.objects.get_or_create(
            title=f"{prefix}_section",
            parent=None,
            defaults={
                "description": "Load-test isolated section.",
                "owner": teacher,
            },
        )
        if section.owner_id != teacher.id:
            section.owner = teacher
            section.save(update_fields=["owner"])

        course, _ = Course.objects.get_or_create(
            title=f"{prefix}_course",
            defaults={
                "description": "Load-test isolated course.",
                "is_open": True,
                "section": section,
                "owner": teacher,
            },
        )
        course.description = "Load-test isolated course."
        course.is_open = True
        course.section = section
        course.owner = teacher
        course.save()

        CourseParticipant.objects.update_or_create(
            course=course,
            user=teacher,
            defaults={"role": CourseParticipant.Role.TEACHER, "is_owner": True},
        )
        for student in students:
            CourseParticipant.objects.update_or_create(
                course=course,
                user=student,
                defaults={"role": CourseParticipant.Role.STUDENT, "is_owner": False},
            )

        fast_problem, _ = Problem.objects.get_or_create(
            title=f"{prefix}_fast_csv_match_problem",
            defaults={
                "statement": "Load-test fast csv_match problem.",
                "rating": 800,
                "is_published": True,
                "author": teacher,
            },
        )
        fast_problem.statement = "Load-test fast csv_match problem."
        fast_problem.rating = 800
        fast_problem.is_published = True
        fast_problem.author = teacher
        fast_problem.save()
        ProblemDescriptor.objects.update_or_create(
            problem=fast_problem,
            defaults={
                "id_column": "id",
                "target_column": "prediction",
                "id_type": "int",
                "target_type": "float",
                "check_order": False,
                "metric_name": "csv_match",
                "metric": "csv_match",
                "metric_code": "",
            },
        )
        fast_data = _save_problem_files(fast_problem, rows=rows, column="prediction")

        real_problem, _ = Problem.objects.get_or_create(
            title=f"{prefix}_real_rmse_problem",
            defaults={
                "statement": "Load-test real rmse problem.",
                "rating": 1000,
                "is_published": True,
                "author": teacher,
            },
        )
        real_problem.statement = "Load-test real rmse problem."
        real_problem.rating = 1000
        real_problem.is_published = True
        real_problem.author = teacher
        real_problem.save()
        ProblemDescriptor.objects.update_or_create(
            problem=real_problem,
            defaults={
                "id_column": "id",
                "target_column": "prediction",
                "id_type": "int",
                "target_type": "float",
                "check_order": False,
                "metric_name": "rmse",
                "metric": "rmse",
                "metric_code": "",
            },
        )
        real_data = _save_problem_files(real_problem, rows=rows, column="prediction")

        contest = None
        if options["create_contest"]:
            contest, _ = Contest.objects.get_or_create(
                title=f"{prefix}_contest",
                defaults={
                    "course": course,
                    "description": "Load-test contest.",
                    "created_by": teacher,
                    "is_published": True,
                    "approval_status": Contest.ApprovalStatus.APPROVED,
                    "start_time": timezone.now() - timedelta(minutes=5),
                    "duration_minutes": None,
                    "allow_upsolving": True,
                },
            )
            contest.course = course
            contest.description = "Load-test contest."
            contest.created_by = teacher
            contest.is_published = True
            contest.approval_status = Contest.ApprovalStatus.APPROVED
            contest.start_time = timezone.now() - timedelta(minutes=5)
            contest.duration_minutes = None
            contest.allow_upsolving = True
            contest.save()
            for position, problem in enumerate((fast_problem, real_problem)):
                ContestProblem.objects.update_or_create(
                    contest=contest,
                    problem=problem,
                    defaults={"position": position},
                )

        payload = {
            "run_id": run_id,
            "prefix": prefix,
            "password": password,
            "teacher": {"id": teacher.id, "username": teacher.username},
            "students": [{"id": user.id, "username": user.username} for user in students],
            "course": {"id": course.id, "title": course.title},
            "fast_problem": {
                "id": fast_problem.id,
                "title": fast_problem.title,
                "answer_rows": rows,
                "answer_file": fast_data.answer_file.name,
            },
            "real_problem": {
                "id": real_problem.id,
                "title": real_problem.title,
                "answer_rows": rows,
                "answer_file": real_data.answer_file.name,
            },
            "contest": {"id": contest.id, "title": contest.title} if contest else None,
            "cleanup": {
                "dry_run": f"python manage.py cleanup_load_test_data --run-id {run_id}",
                "delete": f"python manage.py cleanup_load_test_data --run-id {run_id} --yes",
            },
        }

        output = json.dumps(payload, indent=2, sort_keys=True)
        if options["json"]:
            self.stdout.write(output)
        else:
            self.stdout.write(self.style.SUCCESS("Seeded BOOML load-test data:"))
            self.stdout.write(output)
