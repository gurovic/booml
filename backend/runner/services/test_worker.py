from django.test import TestCase
from unittest.mock import patch, MagicMock
from runner.services.worker import enqueue_submission_for_evaluation, evaluate_submission
from runner.models.submission import Submission

class TasksTestCase(TestCase):

    @patch("runner.services.worker.evaluate_submission.delay")
    def test_enqueue_calls_worker_delay(self, mock_delay):
        submission_id = 1
        result = enqueue_submission_for_evaluation(submission_id)
        mock_delay.assert_called_once_with(submission_id)
        self.assertEqual(result, {"status": "enqueued", "submission_id": submission_id})

    @patch("runner.services.worker.check_submission")
    @patch("runner.services.worker.Submission.objects.get")
    def test_evaluate_submission_calls_checker_and_saves(self, mock_get, mock_checker):
        submission_id = 1

        # Мокаем объект сабмишена
        mock_submission = MagicMock()
        mock_get.return_value = mock_submission

        # Мокаем результат чекера
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.outputs = [{"metric": "accuracy", "value": 0.95}]
        mock_result.errors = []
        mock_checker.return_value = mock_result

        result = evaluate_submission(submission_id)

        # Проверяем вызовы
        mock_get.assert_called_once_with(pk=submission_id)
        mock_checker.assert_called_once_with(mock_submission)
        mock_submission.save.assert_called_once_with(update_fields=['status', 'result_outputs', 'result_errors'])

        # Проверяем поля сабмишена
        self.assertEqual(mock_submission.status, "checked")
        self.assertEqual(mock_submission.result_outputs, mock_result.outputs)
        self.assertEqual(mock_submission.result_errors, mock_result.errors)

        # Проверяем возвращаемое значение
        self.assertEqual(result, {"submission_id": submission_id, "status": "checked"})
