from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock

from runner.services.worker import enqueue_submission_for_evaluation, evaluate_submission
from runner.models import Submission


class TasksTestCase(TestCase):

    @override_settings(RUNNER_USE_CELERY_QUEUE=True)
    @patch("runner.services.worker.evaluate_submission.delay")
    def test_enqueue_calls_worker_delay(self, mock_delay):
        submission_id = 1
        result = enqueue_submission_for_evaluation(submission_id)
        mock_delay.assert_called_once_with(submission_id)
        self.assertEqual(result, {"status": "enqueued", "submission_id": submission_id})

    @override_settings(RUNNER_USE_CELERY_QUEUE=False)
    @patch("runner.services.worker.evaluate_submission")
    def test_enqueue_runs_inline_when_queue_disabled(self, mock_evaluate):
        submission_id = 5
        mock_evaluate.return_value = {"status": "ok"}
        result = enqueue_submission_for_evaluation(submission_id)
        mock_evaluate.assert_called_once_with(submission_id)
        self.assertEqual(result, {"status": "ok"})

    @patch("runner.services.checker.check_submission")
    @patch("runner.models.Submission.objects.get")
    def test_evaluate_submission_calls_checker_and_saves(self, mock_get, mock_checker):
        submission_id = 1

        # Мокаем объект сабмишена
        mock_submission = MagicMock()
        mock_submission.id = submission_id
        mock_get.return_value = mock_submission

        # Мокаем результат чекера
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.outputs = {"metric_score": 0.95, "metric_name": "accuracy"}
        mock_result.errors = []
        mock_checker.return_value = mock_result

        result = evaluate_submission(submission_id)

        # ИСПРАВЛЕНО: используем pk вместо id
        mock_get.assert_called_once_with(pk=submission_id)  # БЫЛО: id=submission_id
        mock_checker.assert_called_once_with(mock_submission)
        mock_submission.save.assert_called_once_with(update_fields=["status", "metrics"])

        # Проверяем поля сабмишена
        self.assertEqual(mock_submission.status, Submission.STATUS_ACCEPTED)
        self.assertEqual(mock_submission.metrics, {
            **mock_result.outputs,
            "metric": mock_result.outputs["metric_score"],
        })

        # Проверяем возвращаемое значение
        self.assertEqual(result, {"submission_id": submission_id, "status": Submission.STATUS_ACCEPTED})

    @patch("runner.services.checker.check_submission")
    @patch("runner.models.Submission.objects.get")
    def test_evaluate_submission_keeps_existing_metric_payload(self, mock_get, mock_checker):
        submission_id = 2
        mock_submission = MagicMock()
        mock_submission.id = submission_id
        mock_submission.metrics = {"accuracy": 0.95, "metric": 0.95}
        mock_get.return_value = mock_submission

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.outputs = {"metric_score": 0.95, "metric_name": "accuracy", "report_id": 10}
        mock_result.errors = []
        mock_checker.return_value = mock_result

        evaluate_submission(submission_id)

        self.assertEqual(mock_submission.status, Submission.STATUS_ACCEPTED)
        self.assertEqual(mock_submission.metrics.get("accuracy"), 0.95)
        self.assertEqual(mock_submission.metrics.get("metric"), 0.95)
        self.assertEqual(mock_submission.metrics.get("metric_name"), "accuracy")
        self.assertEqual(mock_submission.metrics.get("report_id"), 10)

    @patch("runner.services.checker.check_submission")
    @patch("runner.models.Submission.objects.get")
    def test_evaluate_submission_converts_legacy_numeric_metrics(self, mock_get, mock_checker):
        submission_id = 3
        mock_submission = MagicMock()
        mock_submission.id = submission_id
        mock_submission.metrics = 0.81
        mock_get.return_value = mock_submission

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.outputs = {"metric_score": 0.93, "metric_name": "auc"}
        mock_result.errors = []
        mock_checker.return_value = mock_result

        evaluate_submission(submission_id)

        self.assertEqual(mock_submission.status, Submission.STATUS_ACCEPTED)
        self.assertEqual(mock_submission.metrics.get("metric"), 0.93)
        self.assertEqual(mock_submission.metrics.get("metric_score"), 0.93)
        self.assertEqual(mock_submission.metrics.get("metric_name"), "auc")
