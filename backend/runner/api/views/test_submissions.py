import tempfile
from pathlib import Path
from datetime import date
from unittest import mock
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from ...models.problem import Problem
from ...models.submission import Submission

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
        self.url = reverse("submission-create")

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
        self.client.post(self.url, {"problem_id": self.problem.id, "file": f})
        self.assertTrue(mock_enqueue.called)

        mock_preval.is_valid = False
        mock_enqueue.reset_mock()

        f2 = SimpleUploadedFile("preds2.csv", b"id,pred\n1,0.1\n1,0.2\n", content_type="text/csv")
        self.client.post(self.url, {"problem_id": self.problem.id, "file": f2})
        self.assertFalse(mock_enqueue.called)
