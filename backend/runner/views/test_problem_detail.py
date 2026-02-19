import tempfile
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from runner.models import Problem, Submission, ProblemData, ProblemDescriptor

problem_detail_view = import_module("runner.views.problem_detail")


class ProblemDetailViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pass12345")
        self.problem = Problem.objects.create(title="Demo", statement="desc", rating=800)
        self.url = reverse("runner:problem_detail", args=[self.problem.id])

        self.tmpdir = tempfile.TemporaryDirectory()
        self.media_root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _submission_file(self, name: str = "submission.csv"):
        return SimpleUploadedFile(
            name,
            b"id,target\n1,0.5\n",
            content_type="text/csv",
        )

    def _problem_api_url(self):
        return reverse("runner:backend_problem_detail")

    def _problem_download_url(self):
        return reverse("runner:backend_problem_file_download", args=[self.problem.id])

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_get_renders_upload_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertContains(response, "Отправить решение")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_context_for_anonymous_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["submissions"]), 0)
        self.assertIsNone(response.context["result"])

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_problem_data_in_context(self):
        problem_data = ProblemData.objects.create(problem=self.problem)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["data"])
        self.assertEqual(response.context["data"], problem_data)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_problem_data_none_in_context(self):
        ProblemData.objects.filter(problem=self.problem).delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["data"])

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_descriptor_metric_shown_to_user(self):
        ProblemDescriptor.objects.create(
            problem=self.problem,
            id_column="id",
            target_column="prediction",
            metric_name="accuracy",
            metric_code="",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Метрика задачи")
        self.assertContains(response, "accuracy")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_descriptor_marks_custom_metric(self):
        ProblemDescriptor.objects.create(
            problem=self.problem,
            id_column="id",
            target_column="prediction",
            metric_name="macro_iou",
            metric_code="def compute_metric(y_true, y_pred):\n    return {'metric': 1.0}",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "macro_iou")
        self.assertContains(response, "кастомная реализация")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_post_requires_authentication(self):
        response = self.client.post(self.url, {"file": self._submission_file()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Авторизуйтесь")
        self.assertEqual(Submission.objects.count(), 0)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_invalid_form_returns_error(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 0)
        feedback = response.context["submission_feedback"]
        self.assertEqual(feedback["level"], "error")
        self.assertIn("Исправьте ошибки формы", feedback["message"])

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
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

    def test_problem_detail_api_returns_full_file_list_from_root_and_hides_answer(self):
        problem_data_root = self.media_root / "problem_data_root"
        problem_dir = problem_data_root / str(self.problem.id)
        (problem_dir / "train").mkdir(parents=True, exist_ok=True)
        (problem_dir / "test").mkdir(parents=True, exist_ok=True)
        (problem_dir / "sample_submission").mkdir(parents=True, exist_ok=True)
        (problem_dir / "answer").mkdir(parents=True, exist_ok=True)

        (problem_dir / "train" / "b.csv").write_text("id,x\n1,2\n", encoding="utf-8")
        (problem_dir / "train" / "a.csv").write_text("id,x\n3,4\n", encoding="utf-8")
        (problem_dir / "test" / "data.zip").write_bytes(b"PK\x03\x04test")
        (problem_dir / "sample_submission" / "template.csv").write_text("id,target\n1,0\n", encoding="utf-8")
        (problem_dir / "answer" / "secret.csv").write_text("id,target\n1,1\n", encoding="utf-8")

        with override_settings(MEDIA_ROOT=self.media_root, PROBLEM_DATA_ROOT=problem_data_root):
            pdata = ProblemData.objects.create(problem=self.problem)
            # Duplicate name with root source: root file should win via dedupe and ordering.
            pdata.train_file.save("a.csv", ContentFile(b"id,x\n9,9\n"), save=True)
            pdata.test_file.save("fallback_test.csv", ContentFile(b"id,y\n1,1\n"), save=True)

            response = self.client.get(self._problem_api_url(), {"problem_id": self.problem.id})

        self.assertEqual(response.status_code, 200)
        data = response.json()

        actual = [(item["kind"], item["name"]) for item in data["file_list"]]
        self.assertEqual(
            actual,
            [
                ("train", "train.csv"),
                ("test", "test.csv"),
                ("sample_submission", "sample_submission.csv"),
            ],
        )
        self.assertTrue(all(item["kind"] != "answer" for item in data["file_list"]))
        self.assertEqual(data["files"]["train"], data["file_list"][0]["url"])
        self.assertEqual(data["files"]["test"], data["file_list"][1]["url"])
        self.assertEqual(data["files"]["sample_submission"], data["file_list"][2]["url"])

    def test_problem_file_download_reads_from_problem_data_root(self):
        problem_data_root = self.media_root / "problem_data_root"
        train_dir = problem_data_root / str(self.problem.id) / "train"
        train_dir.mkdir(parents=True, exist_ok=True)
        expected = b"PK\x03\x04root-zip"
        (train_dir / "dataset.zip").write_bytes(expected)

        with override_settings(MEDIA_ROOT=self.media_root, PROBLEM_DATA_ROOT=problem_data_root):
            response = self.client.get(
                self._problem_download_url(),
                {"kind": "train", "name": "train.csv"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("train.csv", response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), expected)

    def test_problem_file_download_rejects_path_traversal(self):
        problem_data_root = self.media_root / "problem_data_root"
        with override_settings(MEDIA_ROOT=self.media_root, PROBLEM_DATA_ROOT=problem_data_root):
            response = self.client.get(
                self._problem_download_url(),
                {"kind": "train", "name": "../secret.csv"},
            )

        self.assertEqual(response.status_code, 400)

    def test_problem_file_download_falls_back_to_problem_data_model(self):
        problem_data_root = self.media_root / "problem_data_root"

        with override_settings(MEDIA_ROOT=self.media_root, PROBLEM_DATA_ROOT=problem_data_root):
            pdata = ProblemData.objects.create(problem=self.problem)
            pdata.train_file.save("fallback.csv", ContentFile(b"id,x\n7,8\n"), save=True)

            response = self.client.get(
                self._problem_download_url(),
                {"kind": "train", "name": "train.csv"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("train.csv", response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), b"id,x\n7,8\n")

    def test_problem_detail_api_reads_files_from_media_root_when_external_root_missing(self):
        media_problem_dir = self.media_root / "problem_data" / str(self.problem.id) / "test"
        media_problem_dir.mkdir(parents=True, exist_ok=True)
        (media_problem_dir / "media_only.csv").write_text("id,v\n1,5\n", encoding="utf-8")

        missing_root = self.media_root / "missing_problem_data_root"
        with override_settings(MEDIA_ROOT=self.media_root, PROBLEM_DATA_ROOT=missing_root):
            response = self.client.get(self._problem_api_url(), {"problem_id": self.problem.id})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn({"kind": "test", "name": "test.csv", "url": data["files"]["test"]}, data["file_list"])
