from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course
from runner.views.contest_draft import create_contest

User = get_user_model()


class CreateContestViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.course = Course.objects.create(title="Course A", owner=self.owner)

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

        with patch("runner.views.contest_draft.redirect", return_value=HttpResponse("ok")):
            response = create_contest.__wrapped__(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 200)
        contest = Contest.objects.get(title="Via view")
        self.assertEqual(contest.course, self.course)
        self.assertEqual(contest.created_by, self.teacher)
        self.assertTrue(contest.is_published)
