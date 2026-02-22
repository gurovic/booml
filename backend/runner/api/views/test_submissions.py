import tempfile
from pathlib import Path
from datetime import date, timedelta
from unittest import mock
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from ...models.contest import Contest
from ...models.course import Course, CourseParticipant
from ...models.problem import Problem
from ...models.problem_desriptor import ProblemDescriptor
from ...models.section import Section
from ...models.submission import Submission
from ...models.prevalidation import PreValidation
from ...services.section_service import SectionCreateInput, create_section
from .submissions import SubmissionCreateView, SubmissionDetailView, ProblemSubmissionsListView

User = get_user_model()


class SubmissionAPITests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.media_root = Path(self.tmpdir.name)

        self.user = User.objects.create_user(username="u1", password="pass")
        self.client.login(username="u1", password="pass")
        self.problem = Problem.objects.create(
            title="Demo Problem", statement="predict", created_at=date.today()
        )
        ProblemDescriptor.objects.create(
            problem=self.problem,
            id_column="id",
            target_column="pred",
            target_type="float",
        )
        self.teacher = User.objects.create_user(username="teacher_submissions", password="pass")
        root_section = Section.objects.get(title="Авторские", parent__isnull=True)
        section = create_section(
            SectionCreateInput(
                title="Submissions Section",
                owner=self.teacher,
                parent=root_section,
            )
        )
        self.course = Course.objects.create(
            title="Submissions Course",
            owner=self.teacher,
            section=section,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.teacher,
            role=CourseParticipant.Role.TEACHER,
            is_owner=True,
        )
        CourseParticipant.objects.create(
            course=self.course,
            user=self.user,
            role=CourseParticipant.Role.STUDENT,
        )
        self.contest = Contest.objects.create(
            title="Timed Contest",
            course=self.course,
            created_by=self.teacher,
            is_published=True,
            approval_status=Contest.ApprovalStatus.APPROVED,
            start_time=timezone.now() - timedelta(hours=2),
            duration_minutes=60,
            allow_upsolving=False,
        )
        self.contest.problems.add(self.problem)
        self.url = reverse("submission-create")
        self.factory = APIRequestFactory()

    def tearDown(self):
        self.tmpdir.cleanup()

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    @patch("runner.api.views.submissions.enqueue_submission_for_evaluation")
    def test_upload_valid_csv(self, mock_enqueue):
        mock_enqueue.return_value = {"status": "enqueued", "submission_id": 1}

        f = SimpleUploadedFile("preds.csv", b"id,pred\n1,0.1\n2,0.2\n", content_type="text/csv")
        resp = self.client.post(self.url, {"problem_id": self.problem.id, "file": f})

        self.assertEqual(resp.status_code, 201)
        self.assertIsNotNone(Submission.objects.first())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_invalid_problem_id(self):
        f = SimpleUploadedFile("preds.csv", b"id,pred\n", content_type="text/csv")
        resp = self.client.post(self.url, {"problem_id": 9999, "file": f})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("problem_id", resp.json())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    @patch("runner.api.views.submissions.enqueue_submission_for_evaluation")
    def test_submit_raw_text(self, mock_enqueue):
        raw_text = "id,pred\n1,0.1\n2,0.2\n"
        resp = self.client.post(
            self.url,
            {"problem_id": self.problem.id, "raw_text": raw_text},
        )

        self.assertEqual(resp.status_code, 201)
        submission = Submission.objects.get(problem=self.problem, user=self.user)
        self.assertEqual(submission.source, Submission.SOURCE_TEXT)
        self.assertEqual(submission.raw_text, raw_text)
        self.assertTrue(bool(submission.file))
        self.assertTrue(str(submission.file.name).endswith(".csv"))
        self.assertTrue(mock_enqueue.called)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_reject_file_and_raw_text_together(self):
        f = SimpleUploadedFile("preds.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
        resp = self.client.post(
            self.url,
            {"problem_id": self.problem.id, "file": f, "raw_text": "id,pred\n1,0.1\n"},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertIn("non_field_errors", resp.json())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_reject_submission_after_deadline_without_upsolving(self):
        resp = self.client.post(
            self.url,
            {
                "problem_id": self.problem.id,
                "contest_id": self.contest.id,
                "raw_text": "id,pred\n1,0.1\n",
            },
        )

        self.assertEqual(resp.status_code, 400)
        self.assertIn("contest_id", resp.json())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_reject_submission_before_contest_start(self):
        self.contest.start_time = timezone.now() + timedelta(hours=1)
        self.contest.save(update_fields=["start_time"])

        resp = self.client.post(
            self.url,
            {
                "problem_id": self.problem.id,
                "contest_id": self.contest.id,
                "raw_text": "id,pred\n1,0.1\n",
            },
        )

        self.assertEqual(resp.status_code, 400)
        self.assertIn("contest_id", resp.json())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    @patch("runner.api.views.submissions.enqueue_submission_for_evaluation")
    def test_allow_submission_after_deadline_with_upsolving(self, mock_enqueue):
        self.contest.allow_upsolving = True
        self.contest.save(update_fields=["allow_upsolving"])

        resp = self.client.post(
            self.url,
            {
                "problem_id": self.problem.id,
                "contest_id": self.contest.id,
                "raw_text": "id,pred\n1,0.1\n",
            },
        )

        self.assertEqual(resp.status_code, 201)
        self.assertTrue(mock_enqueue.called)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    @patch("runner.api.views.submissions.enqueue_submission_for_evaluation")
    @patch("runner.services.validation_service.run_pre_validation")
    def test_enqueue_only_if_valid(self, mock_validate, mock_enqueue):
        mock_preval = mock.Mock()
        mock_preval.is_valid = True
        mock_validate.return_value = mock_preval

        f = SimpleUploadedFile("preds.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
        request = self.factory.post(self.url, {"problem_id": self.problem.id, "file": f}, format="multipart")
        force_authenticate(request, user=self.user)
        response = SubmissionCreateView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(mock_enqueue.called)

        mock_preval.is_valid = False
        mock_enqueue.reset_mock()

        f2 = SimpleUploadedFile("preds2.csv", b"id,pred\n1,0.1\n1,0.2\n", content_type="text/csv")
        request2 = self.factory.post(self.url, {"problem_id": self.problem.id, "file": f2}, format="multipart")
        force_authenticate(request2, user=self.user)
        response2 = SubmissionCreateView.as_view()(request2)
        self.assertEqual(response2.status_code, 400)
        self.assertFalse(mock_enqueue.called)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_submission_detail_view(self):
        """Test getting submission details with prevalidation data."""
        f = SimpleUploadedFile("preds.csv", b"id,pred\n1,0.1\n2,0.2\n", content_type="text/csv")
        submission = Submission.objects.create(
            user=self.user,
            problem=self.problem,
            file=f,
            status=Submission.STATUS_ACCEPTED,
            metrics={"accuracy": 0.95}
        )

        # Create a prevalidation report for the submission
        PreValidation.objects.create(
            submission=submission,
            valid=True,
            status="passed",
            errors_count=0,
            warnings_count=1,
            rows_total=2,
            unique_ids=2,
            duration_ms=100,
            warnings=["Some warning"],
            stats={"test_stat": 123}
        )

        detail_url = reverse("submission-detail", kwargs={"pk": submission.id})
        resp = self.client.get(detail_url)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Check basic submission data
        self.assertEqual(data["id"], submission.id)
        self.assertEqual(data["problem_id"], self.problem.id)
        self.assertEqual(data["problem_title"], self.problem.title)
        self.assertEqual(data["status"], Submission.STATUS_ACCEPTED)
        self.assertEqual(data["metrics"]["accuracy"], 0.95)

        # Check file_url is present and is a relative path (not absolute URL)
        self.assertIn("file_url", data)
        self.assertIsNotNone(data["file_url"])
        self.assertIsInstance(data["file_url"], str)
        self.assertTrue(data["file_url"].startswith("/media/submissions/"))
        # Ensure it's not an absolute URL with hostname
        self.assertNotIn("http://", data["file_url"])
        self.assertNotIn("backend:", data["file_url"])

        # Check prevalidation data
        self.assertIn("prevalidation", data)
        self.assertTrue(data["prevalidation"]["valid"])
        self.assertEqual(data["prevalidation"]["status"], "passed")
        self.assertEqual(data["prevalidation"]["rows_total"], 2)
        self.assertEqual(data["prevalidation"]["warnings_count"], 1)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_submission_detail_unauthorized(self):
        """Test that users can only view their own submissions."""
        other_user = User.objects.create_user(username="u2", password="pass")
        f = SimpleUploadedFile("preds.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
        submission = Submission.objects.create(
            user=other_user,
            problem=self.problem,
            file=f,
            status=Submission.STATUS_PENDING
        )

        detail_url = reverse("submission-detail", kwargs={"pk": submission.id})
        resp = self.client.get(detail_url)

        # Should return 404 since the submission doesn't belong to the authenticated user
        self.assertEqual(resp.status_code, 404)


class ProblemSubmissionsListTests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.other_user = User.objects.create_user(username="otheruser", password="testpass")
        self.problem = Problem.objects.create(
            title="Test Problem", statement="test", created_at=date.today()
        )
        self.factory = APIRequestFactory()

    def tearDown(self):
        self.tmpdir.cleanup()

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_list_problem_submissions(self):
        # Create some submissions for the user
        for i in range(5):
            f = SimpleUploadedFile(f"test{i}.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
            Submission.objects.create(user=self.user, problem=self.problem, file=f, status="accepted")

        url = reverse("submission-list-problem", kwargs={"problem_id": self.problem.id})
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)

        response = ProblemSubmissionsListView.as_view()(request, problem_id=self.problem.id)

        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 5)
        self.assertEqual(data["count"], 5)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_list_problem_submissions_pagination(self):
        # Create 15 submissions to test pagination
        for i in range(15):
            f = SimpleUploadedFile(f"test{i}.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
            Submission.objects.create(user=self.user, problem=self.problem, file=f, status="accepted")

        url = reverse("submission-list-problem", kwargs={"problem_id": self.problem.id})

        # Test first page
        request = self.factory.get(url + "?page=1")
        force_authenticate(request, user=self.user)
        response = ProblemSubmissionsListView.as_view()(request, problem_id=self.problem.id)

        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(len(data["results"]), 10)  # Default page size
        self.assertEqual(data["count"], 15)
        self.assertIsNotNone(data["next"])
        self.assertIsNone(data["previous"])

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_list_problem_submissions_only_user_submissions(self):
        # Create submissions for two different users
        f1 = SimpleUploadedFile("test1.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
        Submission.objects.create(user=self.user, problem=self.problem, file=f1, status="accepted")

        f2 = SimpleUploadedFile("test2.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
        Submission.objects.create(user=self.other_user, problem=self.problem, file=f2, status="accepted")

        url = reverse("submission-list-problem", kwargs={"problem_id": self.problem.id})
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)

        response = ProblemSubmissionsListView.as_view()(request, problem_id=self.problem.id)

        self.assertEqual(response.status_code, 200)
        data = response.data
        # User should only see their own submissions
        self.assertEqual(data["count"], 1)

    def test_list_problem_submissions_nonexistent_problem(self):
        url = reverse("submission-list-problem", kwargs={"problem_id": 9999})
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)

        response = ProblemSubmissionsListView.as_view()(request, problem_id=9999)

        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["count"], 0)

    def test_list_problem_submissions_unauthorized(self):
        url = reverse("submission-list-problem", kwargs={"problem_id": self.problem.id})
        request = self.factory.get(url)
        # Don't authenticate the request

        response = ProblemSubmissionsListView.as_view()(request, problem_id=self.problem.id)

        self.assertEqual(response.status_code, 403)
