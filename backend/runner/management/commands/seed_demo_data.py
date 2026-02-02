from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from runner.models import (
    Contest,
    Course,
    CourseParticipant,
    Problem,
    ProblemData,
    ProblemDescriptor,
    Section,
)
from runner.services.section_service import ROOT_SECTION_TITLES


class Command(BaseCommand):
    help = "Seed demo tasks, courses, and contests from bundled JSON data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Seed even if data already exists (only missing items are created).",
        )

    def handle(self, *args, **options):
        data_path = Path(settings.BASE_DIR) / "runner" / "fixtures" / "demo_tasks.json"
        if not data_path.exists():
            self.stdout.write(self.style.WARNING(f"Demo data JSON not found: {data_path}"))
            return

        owner = self._ensure_owner()

        with transaction.atomic():
            problems_by_source_id = self._import_problems(
                data_path,
                owner,
                force_update=options["force"],
            )
            self._ensure_sections_courses_contests(owner, problems_by_source_id)

    def _ensure_owner(self):
        User = get_user_model()
        owner = User.objects.filter(is_superuser=True).order_by("id").first()
        if owner is None:
            owner = User.objects.order_by("id").first()
        if owner is not None:
            return owner

        username = "admin"
        password = "admin"
        create_superuser = getattr(User.objects, "create_superuser", None)
        if callable(create_superuser):
            owner = create_superuser(username=username, password=password)
        else:
            owner = User.objects.create(username=username, is_staff=True, is_superuser=True)
            if hasattr(owner, "set_password"):
                owner.set_password(password)
                owner.save(update_fields=["password"])
        self.stdout.write(self.style.WARNING("Created default admin user (username: admin, password: admin)."))
        return owner

    def _import_problems(self, data_path: Path, owner, *, force_update: bool):
        payload = json.loads(data_path.read_text(encoding="utf-8"))
        rows = payload.get("problems", [])
        problems_by_source_id = {}
        created = 0
        for row in rows:
            source_id = row["id"]
            title = row["title"]
            statement = row.get("statement") or ""
            created_at = row.get("created_at")
            rating = row.get("rating")
            is_published = row.get("is_published")
            problem, was_created = Problem.objects.get_or_create(
                title=title,
                defaults={
                    "statement": statement or "",
                    "created_at": created_at,
                    "rating": rating or 800,
                    "is_published": bool(is_published),
                    "author": owner,
                },
            )
            if not was_created:
                updates = {}
                if force_update and statement is not None:
                    updates["statement"] = statement
                elif not problem.statement and statement:
                    updates["statement"] = statement
                if force_update and rating is not None:
                    updates["rating"] = rating
                elif rating and problem.rating != rating:
                    updates["rating"] = rating
                if force_update and is_published is not None:
                    updates["is_published"] = bool(is_published)
                if updates:
                    Problem.objects.filter(pk=problem.pk).update(**updates)
            problems_by_source_id[source_id] = problem
            if was_created:
                created += 1

        self.stdout.write(f"Imported {created} problems from JSON.")

        pdata_rows = payload.get("problem_data", [])
        pdata_created = 0
        for row in pdata_rows:
            problem = problems_by_source_id.get(row["problem_id"])
            if not problem:
                continue
            _, created = ProblemData.objects.update_or_create(
                problem=problem,
                defaults={
                    "train_file": row.get("train_file") or "",
                    "test_file": row.get("test_file") or "",
                    "sample_submission_file": row.get("sample_submission_file") or "",
                    "answer_file": row.get("answer_file") or "",
                },
            )
            if created:
                pdata_created += 1
        self.stdout.write(f"Imported {pdata_created} problem data records.")

        descriptor_rows = payload.get("problem_descriptors", [])
        desc_created = 0
        for row in descriptor_rows:
            problem = problems_by_source_id.get(row["problem_id"])
            if not problem:
                continue
            _, created = ProblemDescriptor.objects.update_or_create(
                problem=problem,
                defaults={
                    "id_column": row.get("id_column") or "id",
                    "target_column": row.get("target_column") or "prediction",
                    "id_type": row.get("id_type") or "int",
                    "target_type": row.get("target_type") or "float",
                    "check_order": bool(row.get("check_order")),
                    "metric": row.get("metric") or "",
                    "metric_name": row.get("metric_name") or "rmse",
                    "metric_code": row.get("metric_code") or "",
                },
            )
            if created:
                desc_created += 1
        self.stdout.write(f"Imported {desc_created} problem descriptors.")

        return problems_by_source_id

    def _ensure_sections_courses_contests(self, owner, problems_by_source_id):
        roots = {}
        for title in ROOT_SECTION_TITLES:
            section, _ = Section.objects.get_or_create(
                title=title,
                parent=None,
                defaults={"description": "", "owner": owner},
            )
            roots[title] = section

        olymp_section = roots.get("Олимпиады")
        thematic_section = roots.get("Тематические")

        olympiad_courses = OrderedDict(
            [
                ("FAIO 2025 Qualification", [8]),
                ("ML-блиц финал", [9]),
            ]
        )
        thematic_courses = OrderedDict(
            [
                ("Классификация", [1, 2, 3, 5]),
                ("Анализ данных", [4]),
                ("Линейная регрессия", [10, 11, 12]),
                ("Логистическая регрессия", [13, 14, 15]),
                ("Decision Tree", [16, 17, 20]),
                ("kNN", [18]),
                ("SVM", [19]),
                ("PCA", [21]),
            ]
        )

        for title, problem_ids in olympiad_courses.items():
            if not olymp_section:
                continue
            course = self._get_or_create_course("Олимпиады", olymp_section, owner)
            contest = self._get_or_create_contest(title, course, owner)
            self._attach_problems(contest, problem_ids, problems_by_source_id)

        for title, problem_ids in thematic_courses.items():
            if not thematic_section:
                continue
            course = self._get_or_create_course("Тематические задачи", thematic_section, owner)
            contest = self._get_or_create_contest(title, course, owner)
            self._attach_problems(contest, problem_ids, problems_by_source_id)

    def _get_or_create_course(self, title, section, owner):
        course, created = Course.objects.get_or_create(
            title=title,
            section=section,
            defaults={
                "description": "",
                "is_open": True,
                "owner": owner,
            },
        )
        if created:
            CourseParticipant.objects.create(
                course=course,
                user=owner,
                role=CourseParticipant.Role.TEACHER,
                is_owner=True,
            )
        else:
            CourseParticipant.objects.get_or_create(
                course=course,
                user=owner,
                defaults={
                    "role": CourseParticipant.Role.TEACHER,
                    "is_owner": True,
                },
            )
        return course

    def _get_or_create_contest(self, title, course, owner):
        contest, _ = Contest.objects.get_or_create(
            title=title,
            course=course,
            defaults={
                "description": "",
                "source": "seed",
                "created_by": owner,
                "is_published": True,
                "status": Contest.Status.GOING,
                "is_rated": False,
                "registration_type": Contest.Registration.OPEN,
                "scoring": Contest.Scoring.IOI,
                "access_type": Contest.AccessType.PUBLIC,
                "access_token": "",
                "approval_status": Contest.ApprovalStatus.APPROVED,
                "approved_by": owner,
            },
        )
        return contest

    def _attach_problems(self, contest, problem_ids, problems_by_source_id):
        if not problems_by_source_id:
            return
        problems = [
            problems_by_source_id[source_id]
            for source_id in problem_ids
            if source_id in problems_by_source_id
        ]
        if problems:
            contest.problems.add(*problems)
