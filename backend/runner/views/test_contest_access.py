import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from runner.models import Contest, Course, CourseParticipant, Section
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.contest_draft import manage_contest_participants, set_contest_access

User = get_user_model()


class ContestAccessViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
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
        self.contest = Contest.objects.create(
            title="Contest 1",
            course=self.course,
            created_by=self.teacher,
        )

    def test_set_access_to_link_generates_token(self):
        self.contest.approval_status = Contest.ApprovalStatus.APPROVED
        self.contest.save(update_fields=["approval_status"])
        request = self.factory.post(
            "/",
            data=json.dumps({"access_type": "link", "is_published": True}),
            content_type="application/json",
        )
        request.user = self.teacher

        response = set_contest_access.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["access_type"], "link")
        self.assertTrue(payload["is_published"])
        self.assertTrue(payload["access_token"])

    def test_set_access_invalid_type(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"access_type": "unknown"}),
            content_type="application/json",
        )
        request.user = self.teacher

        response = set_contest_access.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 400)

    def test_non_owner_cannot_set_access(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"access_type": "public"}),
            content_type="application/json",
        )
        request.user = self.student

        response = set_contest_access.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 403)

    def test_add_participants(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"user_ids": [self.student.id, self.other.id], "action": "add"}),
            content_type="application/json",
        )
        request.user = self.teacher

        response = manage_contest_participants.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())
        returned_ids = {u["id"] for u in payload["allowed_participants"]}
        self.assertEqual(returned_ids, {self.student.id, self.other.id})
        self.assertEqual(set(self.contest.allowed_participants.values_list("id", flat=True)), returned_ids)

    def test_remove_participants(self):
        self.contest.allowed_participants.add(self.student, self.other)
        request = self.factory.post(
            "/",
            data=json.dumps({"user_ids": [self.other.id], "action": "remove"}),
            content_type="application/json",
        )
        request.user = self.teacher

        response = manage_contest_participants.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 200)
        remaining = set(self.contest.allowed_participants.values_list("id", flat=True))
        self.assertEqual(remaining, {self.student.id})

    def test_invalid_users(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"user_ids": [9999], "action": "add"}),
            content_type="application/json",
        )
        request.user = self.teacher

        response = manage_contest_participants.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 400)

    def test_non_owner_cannot_manage_participants(self):
        request = self.factory.post(
            "/",
            data=json.dumps({"user_ids": [self.other.id], "action": "add"}),
            content_type="application/json",
        )
        request.user = self.student

        response = manage_contest_participants.__wrapped__(request, contest_id=self.contest.id)

        self.assertEqual(response.status_code, 403)
