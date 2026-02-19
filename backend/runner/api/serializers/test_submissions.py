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
from ..views.submissions import SubmissionCreateView

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
        
        # Проверяем что запрос прошел успешно
        self.assertEqual(resp.status_code, 201)
        
        # Проверяем что Submission был создан
        sub = Submission.objects.first()
        self.assertIsNotNone(sub)

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
    @patch("runner.api.views.submissions.enqueue_submission_for_evaluation")
    @patch("runner.services.validation_service.run_pre_validation")
    def test_enqueue_only_if_valid(self, mock_validate, mock_enqueue):
        # Мокаем успешную валидацию
        mock_preval = mock.Mock()
        mock_preval.is_valid = True
        mock_validate.return_value = mock_preval
        
        f = SimpleUploadedFile("preds.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
        request = self.factory.post(self.url, {"problem_id": self.problem.id, "file": f}, format="multipart")
        force_authenticate(request, user=self.user)
        response = SubmissionCreateView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(mock_enqueue.called)

        # Мокаем неуспешную валидацию
        mock_preval.is_valid = False
        mock_enqueue.reset_mock()
        
        f2 = SimpleUploadedFile("preds2.csv", b"id,pred\n1,0.1\n1,0.2\n", content_type="text/csv")
        request2 = self.factory.post(self.url, {"problem_id": self.problem.id, "file": f2}, format="multipart")
        force_authenticate(request2, user=self.user)
        response2 = SubmissionCreateView.as_view()(request2)
        self.assertEqual(response2.status_code, 400)
        self.assertFalse(mock_enqueue.called)
