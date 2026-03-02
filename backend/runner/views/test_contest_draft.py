import json
from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from runner.models import Contest, Course, CourseParticipant, Section
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.contest_draft import create_contest, delete_contest, update_contest

User = get_user_model()


class CreateContestViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Owner Section",
                owner=self.owner,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Course A",
            owner=self.owner,
            section=self.section,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseParticipant.Role.TEACHER,
        )

    def test_create_contest_assigns_course_and_creator(self):
        data = {
            "title": "Via view",
            "description": "",
            "source": "vsoch/2025/final",
            "has_time_limit": True,
            "start_time": "2026-02-20T10:00:00Z",
            "end_time": "2026-02-20T12:00:00Z",
            "allow_upsolving": True,
            "is_published": True,
            "status": 0,
            "scoring": "icpc",
            "registration_type": "approval",
            "is_rated": True,
        }
        request = self.factory.post("/", data=data)
        request.user = self.owner

        response = create_contest.__wrapped__(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 201)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["title"], "Via view")
        self.assertEqual(payload["course"], self.course.id)
        self.assertTrue(payload["is_published"])
        self.assertTrue(payload["is_rated"])
        self.assertEqual(payload["scoring"], "icpc")
        self.assertEqual(payload["registration_type"], "approval")
        self.assertEqual(payload["duration_minutes"], 120)
        self.assertTrue(payload["has_time_limit"])
        self.assertTrue(payload["allow_upsolving"])
        self.assertIsNotNone(payload["start_time"])
        self.assertIsNotNone(payload["end_time"])
        self.assertEqual(payload["status"], 0)

        contest = Contest.objects.get(title="Via view")
        self.assertEqual(contest.course, self.course)
        self.assertEqual(contest.created_by, self.owner)
        self.assertTrue(contest.is_published)
        self.assertTrue(contest.is_rated)
        self.assertEqual(contest.scoring, "icpc")
        self.assertEqual(contest.registration_type, "approval")
        self.assertEqual(contest.duration_minutes, 120)
        self.assertTrue(contest.allow_upsolving)

    def test_non_owner_gets_forbidden(self):
        student = User.objects.create_user(username="student", password="pass")
        data = {
            "title": "Blocked",
            "description": "",
            "source": "",
            "start_time": "",
            "duration_minutes": "",
            "is_published": True,
            "status": 0,
        }
        request = self.factory.post("/", data=data)
        request.user = student

        response = create_contest.__wrapped__(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Contest.objects.filter(title="Blocked").exists())

    def test_teacher_can_create_contest(self):
        data = {
            "title": "Teacher contest",
            "description": "",
            "is_published": False,
            "scoring": "ioi",
        }
        request = self.factory.post("/", data=data)
        request.user = self.teacher

        response = create_contest.__wrapped__(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Contest.objects.filter(title="Teacher contest").exists())

    def test_get_method_not_allowed(self):
        request = self.factory.get("/")
        request.user = self.teacher

        response = create_contest.__wrapped__(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 405)


class DeleteContestViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.other_owner = User.objects.create_user(username="other_owner", password="pass")
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Owner Section",
                owner=self.owner,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Course A",
            owner=self.owner,
            section=self.section,
        )
        self.contest = Contest.objects.create(
            course=self.course,
            title="To delete",
            created_by=self.owner,
        )

    def test_creator_can_delete(self):
        request = self.factory.post("/")
        request.user = self.owner

        response = delete_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Contest.objects.filter(id=self.contest.id).exists())

    def test_non_creator_forbidden(self):
        request = self.factory.post("/")
        request.user = self.other_owner

        response = delete_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Contest.objects.filter(id=self.contest.id).exists())

    def test_admin_can_delete(self):
        admin = User.objects.create_user(username="admin", password="pass", is_staff=True)
        request = self.factory.post("/")
        request.user = admin

        response = delete_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Contest.objects.filter(id=self.contest.id).exists())


class UpdateContestViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(username="owner_update", password="pass")
        self.teacher = User.objects.create_user(username="teacher_update", password="pass")
        self.admin = User.objects.create_user(username="admin_update", password="pass", is_staff=True)
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Update Section",
                owner=self.owner,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Course Update",
            owner=self.owner,
            section=self.section,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.owner,
            role=CourseParticipant.Role.TEACHER,
            is_owner=True,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseParticipant.Role.TEACHER,
        )
        self.contest = Contest.objects.create(
            course=self.course,
            title="Timed contest",
            created_by=self.owner,
            start_time=timezone.make_aware(datetime(2026, 2, 20, 10, 0, 0)),
            duration_minutes=120,
            allow_upsolving=False,
        )

    def test_owner_can_update_contest_timing(self):
        payload = {
            "has_time_limit": True,
            "start_time": "2026-02-20T10:00:00Z",
            "end_time": "2026-02-20T13:30:00Z",
            "allow_upsolving": True,
        }
        request = self.factory.post(
            "/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.owner

        response = update_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        self.contest.refresh_from_db()
        self.assertEqual(self.contest.duration_minutes, 210)
        self.assertTrue(self.contest.allow_upsolving)

    def test_teacher_cannot_update_contest_timing(self):
        payload = {
            "has_time_limit": True,
            "start_time": "2026-02-20T10:00:00Z",
            "end_time": "2026-02-20T13:00:00Z",
            "allow_upsolving": False,
        }
        request = self.factory.post(
            "/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.teacher

        response = update_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 403)
        self.contest.refresh_from_db()
        self.assertEqual(self.contest.duration_minutes, 120)

    def test_admin_can_update_contest_timing(self):
        payload = {
            "has_time_limit": True,
            "start_time": "2026-02-20T10:00:00Z",
            "end_time": "2026-02-20T12:30:00Z",
            "allow_upsolving": False,
        }
        request = self.factory.post(
            "/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.admin

        response = update_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        self.contest.refresh_from_db()
        self.assertEqual(self.contest.duration_minutes, 150)

    def test_owner_gets_validation_error_for_invalid_range(self):
        payload = {
            "has_time_limit": True,
            "start_time": "2026-02-20T10:00:00Z",
            "end_time": "2026-02-20T09:59:00Z",
            "allow_upsolving": True,
        }
        request = self.factory.post(
            "/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.owner

        response = update_contest.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 400)
        self.contest.refresh_from_db()
        self.assertEqual(self.contest.duration_minutes, 120)
