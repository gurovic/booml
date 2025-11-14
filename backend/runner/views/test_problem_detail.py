from importlib import import_module
from types import SimpleNamespace
from unittest.mock import ANY, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from runner.models import Problem, Submission

problem_detail_view = import_module("runner.views.problem_detail")


class ProblemDetailViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pass12345")
        self.problem = Problem.objects.create(title="Demo", statement="desc", rating=800)
        self.url = reverse("runner:problem_detail", args=[self.problem.id])

    def _submission_file(self, name: str = "submission.csv"):
        return SimpleUploadedFile(
            name,
            b"id,target\n1,0.5\n",
            content_type="text/csv",
        )

    def test_get_renders_upload_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertContains(response, "Отправить решение")

    def test_post_requires_authentication(self):
        response = self.client.post(self.url, {"file": self._submission_file()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Авторизуйтесь")
        self.assertEqual(Submission.objects.count(), 0)

    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_successful_submission_enqueues_job(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.return_value = SimpleNamespace(is_valid=True)

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)
        submission = Submission.objects.first()

        mock_pre_validation.assert_called_once_with(submission, descriptor=ANY)
        mock_enqueue.assert_called_once_with(submission.id)

        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "success")
        self.assertIn("тестирующую систему", feedback["message"])

    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_failed_prevalidation_returns_error(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.return_value = SimpleNamespace(is_valid=False, errors=["bad csv"])

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)
        mock_enqueue.assert_not_called()

        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "error")
        self.assertIn("не прошёл", feedback["message"])
