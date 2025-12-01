import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course, CourseParticipant
from runner.views.contest_draft import create_contest

User = get_user_model()


class CreateContestViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.course = Course.objects.create(title="Course A", owner=self.owner)
        CourseParticipant.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseParticipant.Role.TEACHER,
        )

    def test_create_contest_assigns_course_and_creator(self):
        data = {
            "title": "Via view",
            "description": "",
            "source": "",
            "start_time": "",
            "duration_minutes": "",
            "is_published": True,
            "status": 0,
        }
        request = self.factory.post("/", data=data)
        request.user = self.teacher

        response = create_contest.__wrapped__(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 201)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["title"], "Via view")
        self.assertEqual(payload["course"], self.course.id)
        self.assertTrue(payload["is_published"])

        contest = Contest.objects.get(title="Via view")
        self.assertEqual(contest.course, self.course)
        self.assertEqual(contest.created_by, self.teacher)
        self.assertTrue(contest.is_published)

    def test_non_teacher_gets_forbidden(self):
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

    def test_get_method_not_allowed(self):
        request = self.factory.get("/")
        request.user = self.teacher

        response = create_contest.__wrapped__(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 405)
