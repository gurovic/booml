import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course, CourseParticipant, Section
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.contest_draft import create_contest, delete_contest

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
            "start_time": "",
            "duration_minutes": "120",
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
        self.assertEqual(payload["status"], 0)

        contest = Contest.objects.get(title="Via view")
        self.assertEqual(contest.course, self.course)
        self.assertEqual(contest.created_by, self.owner)
        self.assertTrue(contest.is_published)
        self.assertTrue(contest.is_rated)
        self.assertEqual(contest.scoring, "icpc")
        self.assertEqual(contest.registration_type, "approval")
        self.assertEqual(contest.duration_minutes, 120)

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
