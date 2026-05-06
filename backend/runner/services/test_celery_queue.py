import time
from unittest.mock import MagicMock, patch

from celery.contrib.testing.worker import start_worker
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings

from runner.celery import app as celery_app
from runner.celery import configure_celery_app
from runner.models import Problem, ProblemDescriptor, Submission
from runner.services.worker import enqueue_submission_for_evaluation


@override_settings(
    RUNNER_USE_CELERY_QUEUE=True,
    CELERY_TASK_ALWAYS_EAGER=False,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CELERY_TASK_DEFAULT_QUEUE="celery_test",
    CELERY_BROKER_URL="memory://localhost/",
    CELERY_RESULT_BACKEND="cache+memory://",
)
class CeleryQueueExecutionTest(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="tester")
        self.problem = Problem.objects.create(title="Test problem")
        ProblemDescriptor.objects.create(problem=self.problem)

    def test_task_runs_via_celery_worker(self):
        submission = Submission.objects.create(
            user=self.user,
            problem=self.problem,
            status=Submission.STATUS_PENDING,
        )

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.outputs = {"metric_score": 1.0}
        mock_result.errors = []

        configure_celery_app()
        # Pin the app to the in-memory broker so the external worker can't consume this task.
        celery_app.conf.update(
            broker_url="memory://localhost/",
            result_backend="cache+memory://",
            task_always_eager=False,
            task_eager_propagates=True,
            task_default_queue="celery_test",
        )
        celery_app.set_current()
        celery_app.set_default()
        with start_worker(celery_app, pool="solo", perform_ping_check=False, loglevel="WARNING"):
            with patch("runner.services.checker.check_submission", return_value=mock_result):
                result = enqueue_submission_for_evaluation(submission.id)
                self.assertEqual(result, {"status": "enqueued", "submission_id": submission.id})

                deadline = time.time() + 5
                while time.time() < deadline:
                    submission.refresh_from_db()
                    if submission.status != Submission.STATUS_PENDING:
                        break
                    time.sleep(0.05)

        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.STATUS_ACCEPTED)
        self.assertEqual(submission.metrics.get("metric"), 1.0)
