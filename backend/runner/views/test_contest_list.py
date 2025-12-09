import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course, CourseParticipant
from runner.views.contest_draft import list_contests

User = get_user_model()


class ContestListViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.outsider = User.objects.create_user(username="outsider", password="pass")
        self.other_teacher = User.objects.create_user(username="other", password="pass")

        self.course = Course.objects.create(title="Course A", owner=self.teacher)
        CourseParticipant.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseParticipant.Role.TEACHER,
            is_owner=True,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.student,
            role=CourseParticipant.Role.STUDENT,
        )

        self.other_course = Course.objects.create(title="Course B", owner=self.other_teacher)
        CourseParticipant.objects.create(
            course=self.other_course,
            user=self.other_teacher,
            role=CourseParticipant.Role.TEACHER,
            is_owner=True,
        )

        self.published = Contest.objects.create(
            title="Published",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
        )
        self.draft = Contest.objects.create(
            title="Draft",
            course=self.course,
            created_by=self.teacher,
            is_published=False,
        )
        self.other_contest = Contest.objects.create(
            title="Other Course",
            course=self.other_course,
            created_by=self.other_teacher,
            is_published=True,
        )

    def test_teacher_sees_contests_for_their_course(self):
        request = self.factory.get("/")
        request.user = self.teacher

        response = list_contests(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        titles = {item["title"] for item in payload["items"]}
        self.assertEqual(titles, {"Published", "Draft"})

    def test_student_sees_only_published(self):
        request = self.factory.get("/")
        request.user = self.student

        response = list_contests(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        titles = [item["title"] for item in payload["items"]]
        self.assertEqual(titles, ["Published"])

    def test_outsider_sees_nothing(self):
        request = self.factory.get("/")
        request.user = self.outsider

        response = list_contests(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["items"], [])

    def test_requires_authentication(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()

        response = list_contests(request)

        self.assertEqual(response.status_code, 401)

    def test_course_filter(self):
        request = self.factory.get("/", {"course_id": str(self.course.id)})
        request.user = self.teacher

        response = list_contests(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        titles = [item["title"] for item in payload["items"]]
        self.assertEqual(set(titles), {"Published", "Draft"})
        self.assertNotIn("Other Course", titles)

    def test_invalid_course_filter_returns_bad_request(self):
        request = self.factory.get("/", {"course_id": "abc"})
        request.user = self.teacher

        response = list_contests(request)

        self.assertEqual(response.status_code, 400)
