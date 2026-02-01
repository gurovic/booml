from __future__ import annotations

import sqlite3
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
    help = "Seed demo tasks, courses, and contests from bundled sqlite database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sqlite-path",
            default=str(Path(settings.BASE_DIR) / "db.sqlite3"),
            help="Path to sqlite database with demo problems.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Seed even if data already exists (only missing items are created).",
        )

    def handle(self, *args, **options):
        sqlite_path = Path(options["sqlite_path"]).resolve()
        if not sqlite_path.exists():
            self.stdout.write(self.style.WARNING(f"SQLite seed DB not found: {sqlite_path}"))
            return

        owner = self._ensure_owner()

        with transaction.atomic():
            problems_by_source_id = self._import_problems(
                sqlite_path,
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

    def _import_problems(self, sqlite_path: Path, owner, *, force_update: bool):
        conn = sqlite3.connect(str(sqlite_path))
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, statement, created_at, rating, is_published "
            "FROM runner_problem ORDER BY id"
        )
        rows = cur.fetchall()
        problems_by_source_id = {}
        created = 0
        for row in rows:
            source_id, title, statement, created_at, rating, is_published = row
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

        self.stdout.write(f"Imported {created} problems from sqlite.")

        cur.execute(
            "SELECT problem_id, train_file, test_file, sample_submission_file, answer_file "
            "FROM runner_problemdata ORDER BY id"
        )
        pdata_rows = cur.fetchall()
        pdata_created = 0
        for problem_id, train, test, sample, answer in pdata_rows:
            problem = problems_by_source_id.get(problem_id)
            if not problem:
                continue
            _, created = ProblemData.objects.update_or_create(
                problem=problem,
                defaults={
                    "train_file": train or "",
                    "test_file": test or "",
                    "sample_submission_file": sample or "",
                    "answer_file": answer or "",
                },
            )
            if created:
                pdata_created += 1
        self.stdout.write(f"Imported {pdata_created} problem data records.")

        cur.execute(
            "SELECT problem_id, id_column, target_column, id_type, target_type, "
            "check_order, metric, metric_name, metric_code "
            "FROM runner_problemdescriptor ORDER BY id"
        )
        descriptor_rows = cur.fetchall()
        desc_created = 0
        for (
            problem_id,
            id_column,
            target_column,
            id_type,
            target_type,
            check_order,
            metric,
            metric_name,
            metric_code,
        ) in descriptor_rows:
            problem = problems_by_source_id.get(problem_id)
            if not problem:
                continue
            _, created = ProblemDescriptor.objects.update_or_create(
                problem=problem,
                defaults={
                    "id_column": id_column or "id",
                    "target_column": target_column or "prediction",
                    "id_type": id_type or "int",
                    "target_type": target_type or "float",
                    "check_order": bool(check_order),
                    "metric": metric or "",
                    "metric_name": metric_name or "rmse",
                    "metric_code": metric_code or "",
                },
            )
            if created:
                desc_created += 1
        self.stdout.write(f"Imported {desc_created} problem descriptors.")

        conn.close()
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
        author_root = roots.get("Авторские")

        author_section = None
        if author_root:
            author_section_title = f"Авторские: {owner.username}"[:255]
            author_section, _ = Section.objects.get_or_create(
                title=author_section_title,
                parent=author_root,
                owner=owner,
                defaults={"description": ""},
            )

        olympiad_courses = OrderedDict(
            [
                ("FAIO 2025 Qualification", [8]),
                ("ML-блиц финал", [9]),
            ]
        )
        author_courses = OrderedDict(
            [
                ("Классификация", [1, 2, 3, 4, 5]),
                ("Тестовые задания", [6, 7]),
                ("Линейная регрессия", [10, 11, 12]),
                ("Логистическая регрессия", [13, 14, 15]),
                ("Decision stump", [16, 17]),
                ("kNN", [18]),
                ("SVM", [19]),
                ("Decision Tree", [20]),
                ("PCA", [21]),
            ]
        )

        for title, problem_ids in olympiad_courses.items():
            if not olymp_section:
                continue
            course = self._get_or_create_course(title, olymp_section, owner)
            contest = self._get_or_create_contest(title, course, owner)
            self._attach_problems(contest, problem_ids, problems_by_source_id)

        for title, problem_ids in author_courses.items():
            if not author_section:
                continue
            course = self._get_or_create_course(title, author_section, owner)
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
