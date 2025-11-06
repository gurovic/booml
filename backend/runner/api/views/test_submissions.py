from datetime import date
from unittest import mock
from unittest.mock import patch
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from runner.models.problem import Problem
from runner.models.submission import Submission

User = get_user_model()

class SubmissionAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass")
        self.client.login(username="u1", password="pass")
        self.problem = Problem.objects.create(
            title="Demo Problem", statement="predict", created_at=date.today()
        )
        self.url = reverse("submission-create")

    @patch("runner.api.views.submissions.enqueue_submission_for_evaluation.delay", lambda *a, **k: None)
    def test_upload_valid_csv(self):
        f = SimpleUploadedFile("preds.csv", b"id,pred\n1,0.1\n2,0.2\n", content_type="text/csv")
        resp = self.client.post(self.url, {"problem_id": self.problem.id, "file": f}, format="multipart")
        self.assertEqual(resp.status_code, 201)
        sub = Submission.objects.get(id=resp.data["id"])
        self.assertEqual(sub.status, "validated")

    def test_invalid_problem_id(self):
        f = SimpleUploadedFile("preds.csv", b"id,pred\n", content_type="text/csv")
        resp = self.client.post(self.url, {"problem_id": 9999, "file": f}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("problem_id", resp.data)

    @patch("runner.api.views.submissions.enqueue_submission_for_evaluation.delay")
    @patch("runner.api.views.submissions.run_pre_validation")
    def test_enqueue_only_if_valid(self, mock_validate, mock_enqueue):
        mock_validate.return_value = mock.Mock(valid=True)
        f = SimpleUploadedFile("preds.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
        self.client.post(self.url, {"problem_id": self.problem.id, "file": f}, format="multipart")
        self.assertTrue(mock_enqueue.called)

        mock_validate.return_value = mock.Mock(valid=False)
        f2 = SimpleUploadedFile("preds2.csv", b"id,pred\n1,0.1\n1,0.2\n", content_type="text/csv")
        self.client.post(self.url, {"problem_id": self.problem.id, "file": f2}, format="multipart")
        self.assertEqual(mock_enqueue.call_count, 1)  # не увеличилось
