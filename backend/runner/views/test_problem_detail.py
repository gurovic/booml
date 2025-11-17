from importlib import import_module
from types import SimpleNamespace
from unittest.mock import ANY, patch
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from runner.models import Problem, Submission, ProblemData

problem_detail_view = import_module("runner.views.problem_detail")


class ProblemDetailViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pass12345")
        self.problem = Problem.objects.create(title="Demo", statement="desc", rating=800)
        self.url = reverse("runner:problem_detail", args=[self.problem.id])

        self.runs_dir = Path('backend/data/runner/runs')
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._cleanup_submission_files()

    def _submission_file(self, name: str = "submission.csv"):
        return SimpleUploadedFile(
            name,
            b"id,target\n1,0.5\n",
            content_type="text/csv",
        )

    def _cleanup_submission_files(self):
        for submission in Submission.objects.all():
            if submission.file and os.path.exists(submission.file.path):
                try:
                    os.remove(submission.file.path)
                except OSError:
                    pass

    def test_get_renders_upload_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertContains(response, "Отправить решение")

    def test_context_for_anonymous_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["submissions"]), 0)
        self.assertIsNone(response.context["result"])

    def test_problem_data_in_context(self):
        problem_data = ProblemData.objects.create(problem=self.problem)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["data"])
        self.assertEqual(response.context["data"], problem_data)

    def test_problem_data_none_in_context(self):
        ProblemData.objects.filter(problem=self.problem).delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["data"])

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    def test_post_requires_authentication(self):
        response = self.client.post(self.url, {"file": self._submission_file()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Авторизуйтесь")
        self.assertEqual(Submission.objects.count(), 0)

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    def test_invalid_form_returns_error(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 0)
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "error")
        self.assertIn("Исправьте ошибки формы", feedback["message"])

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
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

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
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

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_submission_with_none_report_enqueues_job(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.return_value = None

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)
        mock_enqueue.assert_called_once()
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "success")

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_submission_with_valid_attribute(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.return_value = SimpleNamespace(valid=True)

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        mock_enqueue.assert_called_once()
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "success")

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_submission_with_success_status(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.return_value = SimpleNamespace(status="success")

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        mock_enqueue.assert_called_once()
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "success")

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_submission_with_failed_status(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.return_value = SimpleNamespace(status="failed", errors=["Validation failed"])

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        mock_enqueue.assert_not_called()
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "error")
        self.assertIn("не прошёл", feedback["message"])

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_submission_with_error_status(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.return_value = SimpleNamespace(status="error", errors=["Internal error"])

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        mock_enqueue.assert_not_called()
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "error")

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_prevalidation_exception_handling(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.side_effect = Exception("Service unavailable")

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        mock_enqueue.assert_not_called()
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "error")
        self.assertIn("Не удалось запустить", feedback["message"])
        self.assertIn("Service unavailable", feedback["details"])

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_submission_with_list_errors(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.return_value = SimpleNamespace(
            is_valid=False,
            errors=["Error 1", "Error 2"]
        )

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        mock_enqueue.assert_not_called()
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "error")
        self.assertEqual(feedback["details"], "Error 1")

    @override_settings(MEDIA_ROOT='backend/data/runner/runs')
    @patch.object(problem_detail_view, "enqueue_submission_for_evaluation")
    @patch.object(problem_detail_view.validation_service, "run_pre_validation")
    def test_submission_with_string_errors(self, mock_pre_validation, mock_enqueue):
        self.client.force_login(self.user)
        mock_pre_validation.return_value = SimpleNamespace(
            is_valid=False,
            errors="Single error message"
        )

        response = self.client.post(self.url, {"file": self._submission_file()})

        self.assertEqual(response.status_code, 200)
        mock_enqueue.assert_not_called()
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "error")
        self.assertEqual(feedback["details"], "Single error message")