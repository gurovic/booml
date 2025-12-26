import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course, CourseParticipant, Section
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.contest_draft import list_contests

User = get_user_model()


class ContestListViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.outsider = User.objects.create_user(username="outsider", password="pass")
        self.other_teacher = User.objects.create_user(username="other", password="pass")

        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.other_root_section = Section.objects.get(title="Тематические", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Teacher Section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.other_section = create_section(
            SectionCreateInput(
                title="Other Section",
                owner=self.other_teacher,
                parent=self.other_root_section,
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

        self.other_course = Course.objects.create(
            title="Course B",
            owner=self.other_teacher,
            section=self.other_section,
        )
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
            approval_status=Contest.ApprovalStatus.APPROVED,
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
            approval_status=Contest.ApprovalStatus.APPROVED,
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

    def test_private_contest_visible_only_to_allowed(self):
        private_contest = Contest.objects.create(
            title="Private",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            access_type=Contest.AccessType.PRIVATE,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )
        private_contest.allowed_participants.add(self.student)

        request_student = self.factory.get("/")
        request_student.user = self.student
        resp_student = list_contests(request_student)
        titles_student = {item["title"] for item in json.loads(resp_student.content.decode())["items"]}
        self.assertIn("Private", titles_student)

        request_outsider = self.factory.get("/")
        request_outsider.user = self.outsider
        resp_outsider = list_contests(request_outsider)
        titles_outsider = {item["title"] for item in json.loads(resp_outsider.content.decode())["items"]}
        self.assertNotIn("Private", titles_outsider)
