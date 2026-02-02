import tempfile
from pathlib import Path
from datetime import date
from unittest import mock
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate
from ...models.problem import Problem
from ...models.problem_desriptor import ProblemDescriptor
from ...models.submission import Submission
from .submissions import SubmissionCreateView, ProblemSubmissionsListView

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
