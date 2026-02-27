import json
import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings

from runner.models import Contest, ContestProblem, Course, CourseParticipant, Problem, Section, Submission
from runner.services.section_service import SectionCreateInput, create_section
from runner.views.contest_draft import contest_submissions

User = get_user_model()


class ContestSubmissionsViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = User.objects.create_user(username="teacher_submissions_view", password="pass")
        self.teacher_outsider = User.objects.create_user(username="teacher_outsider", password="pass")
        self.student_1 = User.objects.create_user(username="student_sub_1", password="pass")
        self.student_2 = User.objects.create_user(username="student_sub_2", password="pass")

        self.root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        self.section = create_section(
            SectionCreateInput(
                title="Contest submissions section",
                owner=self.teacher,
                parent=self.root_section,
            )
        )
        self.course = Course.objects.create(
            title="Contest submissions course",
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
            user=self.student_1,
            role=CourseParticipant.Role.STUDENT,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.student_2,
            role=CourseParticipant.Role.STUDENT,
        )

        self.contest = Contest.objects.create(
            title="Contest submissions",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
        )

        self.problem_1 = Problem.objects.create(title="Problem 1", statement="...", created_at=date.today())
        self.problem_2 = Problem.objects.create(title="Problem 2", statement="...", created_at=date.today())
        self.problem_outside = Problem.objects.create(
            title="Outside problem",
            statement="...",
            created_at=date.today(),
        )
        ContestProblem.objects.create(contest=self.contest, problem=self.problem_1, position=0)
        ContestProblem.objects.create(contest=self.contest, problem=self.problem_2, position=1)

        self.student_submission_with_file = Submission.objects.create(
            user=self.student_1,
            problem=self.problem_1,
            file=SimpleUploadedFile("student_1.csv", b"id,pred\n1,1\n", content_type="text/csv"),
            status=Submission.STATUS_ACCEPTED,
            metrics={"score": 91.5},
        )
        self.student_submission_plain = Submission.objects.create(
            user=self.student_2,
            problem=self.problem_2,
            status=Submission.STATUS_FAILED,
            metrics={"score": 0},
        )
        self.teacher_submission = Submission.objects.create(
            user=self.teacher,
            problem=self.problem_1,
            status=Submission.STATUS_ACCEPTED,
            metrics={"score": 100},
        )
        self.outside_problem_submission = Submission.objects.create(
            user=self.student_1,
            problem=self.problem_outside,
            status=Submission.STATUS_ACCEPTED,
            metrics={"score": 77},
        )

    def _request(self, user, *, query: str = ""):
        request = self.factory.get(f"/backend/contest/{self.contest.id}/submissions/{query}")
        request.user = user
        return contest_submissions(request, contest_id=self.contest.id)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_teacher_sees_only_student_submissions_inside_contest(self):
        response = self._request(self.teacher)
        self.assertEqual(response.status_code, 200)

        payload = json.loads(response.content.decode())
        ids = {row["id"] for row in payload["results"]}

        self.assertEqual(ids, {self.student_submission_with_file.id, self.student_submission_plain.id})
        self.assertEqual(payload["count"], 2)

        row_by_id = {row["id"]: row for row in payload["results"]}
        file_row = row_by_id[self.student_submission_with_file.id]
        self.assertEqual(file_row["username"], self.student_1.username)
        self.assertEqual(file_row["problem_label"], "A")
        self.assertTrue(file_row["is_csv_file"])
        self.assertTrue(str(file_row["file_url"]).startswith("/media/submissions/"))

    def test_student_is_forbidden(self):
        response = self._request(self.student_1)
        self.assertEqual(response.status_code, 403)

    def test_teacher_from_another_course_is_forbidden(self):
        response = self._request(self.teacher_outsider)
        self.assertEqual(response.status_code, 403)

    def test_pagination(self):
        for idx in range(23):
            Submission.objects.create(
                user=self.student_1,
                problem=self.problem_1,
                status=Submission.STATUS_ACCEPTED,
                metrics={"score": idx},
            )

        response = self._request(self.teacher, query="?page=2&page_size=10")
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode())

        self.assertEqual(payload["count"], 25)
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["page_size"], 10)
        self.assertEqual(payload["total_pages"], 3)
        self.assertEqual(len(payload["results"]), 10)
