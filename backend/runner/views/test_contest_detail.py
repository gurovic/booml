import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from runner.models import Contest, ContestProblem, Course, CourseParticipant, Problem, Section
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.contest_draft import contest_detail
from runner.views.course import course_detail

User = get_user_model()


class ContestDetailViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.outsider = User.objects.create_user(username="outsider", password="pass")
        self.admin = User.objects.create_user(
            username="admin",
            password="pass",
            is_staff=True,
            is_superuser=True,
        )
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Teacher Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Course A",
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
        CourseParticipant.objects.create(
            course=self.course,
            user=self.admin,
            role=CourseParticipant.Role.TEACHER,
            is_owner=False,
        )
        self.contest = Contest.objects.create(
            title="Contest 1",
            description="Desc",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        self.private_contest = Contest.objects.create(
            title="Private",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            access_type=Contest.AccessType.PRIVATE,
            approval_status=Contest.ApprovalStatus.APPROVED,
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
        self.assertTrue(payload["can_edit"])

    def test_student_sees_public_contest_without_token_or_allowed(self):
        request = self.factory.get("/")
        request.user = self.student

        response = contest_detail(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertIsNone(payload["access_token"])
        self.assertEqual(payload["allowed_participants"], [])
        self.assertFalse(payload["can_edit"])

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

    def test_scheduled_contest_hides_problems_for_student_before_start(self):
        self.contest.start_time = timezone.now() + timedelta(hours=1)
        self.contest.duration_minutes = 90
        self.contest.save(update_fields=["start_time", "duration_minutes"])

        request = self.factory.get("/")
        request.user = self.student

        response = contest_detail(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["problems"], [])
        self.assertEqual(payload["problems_count"], 0)
        self.assertFalse(payload["can_view_problems"])

    def test_problems_include_stable_letter_labels_by_contest_order(self):
        p1 = Problem.objects.create(title="P1", statement="...")
        p2 = Problem.objects.create(title="P2", statement="...")
        p3 = Problem.objects.create(title="P3", statement="...")
        ContestProblem.objects.create(contest=self.contest, problem=p1, position=0)
        ContestProblem.objects.create(contest=self.contest, problem=p2, position=2)
        ContestProblem.objects.create(contest=self.contest, problem=p3, position=1)

        request = self.factory.get("/")
        request.user = self.teacher
        response = contest_detail(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        problems = payload["problems"]

        self.assertEqual([row["id"] for row in problems], [p1.id, p3.id, p2.id])
        self.assertEqual([row["index"] for row in problems], [0, 1, 2])
        self.assertEqual([row["label"] for row in problems], ["A", "B", "C"])

    def test_unpublished_problems_are_hidden_in_contest_detail(self):
        p_public = Problem.objects.create(title="Visible", statement="...", is_published=True)
        p_hidden = Problem.objects.create(title="Hidden", statement="...", is_published=False)
        ContestProblem.objects.create(contest=self.contest, problem=p_public, position=0)
        ContestProblem.objects.create(contest=self.contest, problem=p_hidden, position=1)

        request = self.factory.get("/")
        request.user = self.teacher
        response = contest_detail(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["problems_count"], 1)
        self.assertEqual([row["id"] for row in payload["problems"]], [p_public.id])


class CourseDetailViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.outsider = User.objects.create_user(username="outsider", password="pass")
        self.admin = User.objects.create_user(
            username="admin",
            password="pass",
            is_staff=True,
            is_superuser=True,
        )
        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Teacher Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
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
        CourseParticipant.objects.create(
            course=self.course,
            user=self.admin,
            role=CourseParticipant.Role.TEACHER,
            is_owner=False,
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

    def test_outsider_can_view_open_course(self):
        self.course.is_open = True
        self.course.save(update_fields=["is_open"])
        request = self.factory.get("/")
        request.user = self.outsider

        response = course_detail(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 200)
