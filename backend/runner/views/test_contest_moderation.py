import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course, CourseParticipant, Section
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.course import course_contests
from runner.views.contest_draft import list_pending_contests, moderate_contest

User = get_user_model()


class ContestModerationViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(username="admin", password="pass", is_staff=True)
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.root_section = Section.objects.get(title="Авторское", parent__isnull=True)
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
        self.pending_contest = Contest.objects.create(
            title="Pending",
            course=self.course,
            created_by=self.teacher,
            is_published=False,
        )

    def test_admin_sees_pending_list(self):
        request = self.factory.get("/")
        request.user = self.admin

        response = list_pending_contests(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        titles = [item["title"] for item in payload["items"]]
        self.assertIn("Pending", titles)

    def test_non_admin_cannot_see_pending_list(self):
        request = self.factory.get("/")
        request.user = self.teacher

        response = list_pending_contests(request)

        self.assertEqual(response.status_code, 403)

    def test_admin_can_approve_and_publish(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"action": "approve", "publish": True}),
            content_type="application/json",
        )
        request.user = self.admin

        response = moderate_contest.__wrapped__(request, contest_id=self.pending_contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["approval_status"], Contest.ApprovalStatus.APPROVED)
        self.assertTrue(payload["is_published"])

        self.pending_contest.refresh_from_db()
        self.assertEqual(self.pending_contest.approval_status, Contest.ApprovalStatus.APPROVED)
        self.assertTrue(self.pending_contest.is_published)

    def test_admin_can_reject(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"action": "reject"}),
            content_type="application/json",
        )
        request.user = self.admin

        response = moderate_contest.__wrapped__(request, contest_id=self.pending_contest.id)

        self.assertEqual(response.status_code, 200)
        self.pending_contest.refresh_from_db()
        self.assertEqual(self.pending_contest.approval_status, Contest.ApprovalStatus.REJECTED)
        self.assertFalse(self.pending_contest.is_published)

    def test_course_contests_for_member(self):
        self.pending_contest.approval_status = Contest.ApprovalStatus.APPROVED
        self.pending_contest.is_published = True
        self.pending_contest.save(update_fields=["approval_status", "is_published"])

        request = self.factory.get("/")
        request.user = self.student

        response = course_contests(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        titles = [item["title"] for item in payload["items"]]
        self.assertIn("Pending", titles)

    def test_course_contests_denies_non_member(self):
        outsider = User.objects.create_user(username="outsider", password="pass")
        request = self.factory.get("/")
        request.user = outsider

        response = course_contests(request, course_id=self.course.id)

        self.assertEqual(response.status_code, 403)
