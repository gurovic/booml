import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course, CourseParticipant, Problem, Section
from runner.views.contest_draft import contest_detail, course_detail

User = get_user_model()


class ContestDetailViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.outsider = User.objects.create_user(username="outsider", password="pass")
        self.section = Section.objects.create(title="Авторское", owner=self.teacher)
        self.course = Course.objects.create(title="Course A", owner=self.teacher, section=self.section)
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
        self.contest = Contest.objects.create(
            title="Contest 1",
            description="Desc",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
        )
        self.problem = Problem.objects.create(title="Two Sum", statement="add numbers")
        self.contest.problems.add(self.problem)
        self.private_contest = Contest.objects.create(
            title="Private",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            access_type=Contest.AccessType.PRIVATE,
        )
        self.private_contest.allowed_participants.add(self.student)

    def test_teacher_sees_allowed_participants_and_token(self):
        self.contest.access_type = Contest.AccessType.LINK
        self.contest.access_token = "token123"
        self.contest.save()

        request = self.factory.get("/")
        request.user = self.teacher

        response = contest_detail(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["title"], "Contest 1")
        self.assertEqual(payload["description"], "Desc")
        self.assertEqual(payload["course"], self.course.id)
        self.assertEqual(payload["access_type"], "link")
        self.assertEqual(payload["access_token"], "token123")
        self.assertEqual(payload["allowed_participants"], [])
        self.assertEqual(len(payload["problems"]), 1)
        self.assertEqual(payload["problems"][0]["id"], self.problem.id)

    def test_student_sees_public_contest_without_token_or_allowed(self):
        request = self.factory.get("/")
        request.user = self.student

        response = contest_detail(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertIsNone(payload["access_token"])
        self.assertEqual(payload["allowed_participants"], [])
        self.assertEqual(len(payload["problems"]), 1)

    def test_private_contest_access_denied_for_not_allowed_student(self):
        request = self.factory.get("/")
        request.user = self.outsider

        response = contest_detail(request, contest_id=self.private_contest.id)

        self.assertEqual(response.status_code, 403)

    def test_private_contest_allowed_student_can_view(self):
        request = self.factory.get("/")
        request.user = self.student

        response = contest_detail(request, contest_id=self.private_contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["title"], "Private")
        self.assertEqual(payload["allowed_participants"], [])
        self.assertEqual(payload["problems"], [])


class CourseDetailViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.outsider = User.objects.create_user(username="outsider", password="pass")
        self.section = Section.objects.create(title="Авторское", owner=self.teacher)
        self.course = Course.objects.create(
            title="Course A",
            description="Desc",
            owner=self.teacher,
            section=self.section,
        )
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

    def test_teacher_gets_course_with_participants(self):
        request = self.factory.get("/")
        request.user = self.teacher

        response = course_detail(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        usernames = {p["username"] for p in payload["participants"]}
        self.assertEqual(usernames, {"teacher", "student"})

    def test_student_can_view_course(self):
        request = self.factory.get("/")
        request.user = self.student

        response = course_detail(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 200)

    def test_outsider_forbidden(self):
        request = self.factory.get("/")
        request.user = self.outsider

        response = course_detail(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 403)
