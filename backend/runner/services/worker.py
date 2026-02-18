import logging
from django.conf import settings
from kombu.exceptions import OperationalError as KombuOperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

from runner.celery import app as celery_app
from runner.models.submission import Submission
from runner.services import checker as checker_service

logger = logging.getLogger(__name__)


def _use_celery_queue() -> bool:
    return getattr(settings, "RUNNER_USE_CELERY_QUEUE", False)

def _should_run_inline_for_broker() -> bool:
    broker_url = (celery_app.conf.broker_url or "").lower()
    return broker_url.startswith("memory://")


@celery_app.task
def enqueue_submission_for_evaluation(submission_id: int):
    logger.info(f"[QUEUE] Submission {submission_id} added to evaluation queue.")
    if not _use_celery_queue():
        logger.info("[QUEUE] Celery queue disabled; running submission %s inline.", submission_id)
        return evaluate_submission(submission_id)

    if _should_run_inline_for_broker():
        logger.info(
            "[QUEUE] In-memory broker detected; running submission %s inline.",
            submission_id,
        )
        evaluate_submission(submission_id)
        return {"status": "enqueued", "submission_id": submission_id}

    try:
        evaluate_submission.delay(submission_id)
        return {"status": "enqueued", "submission_id": submission_id}
    except (KombuOperationalError, RedisConnectionError, ConnectionError) as exc:
        logger.warning(
            "[QUEUE] Celery broker unavailable; running submission %s inline. %s",
            submission_id,
            exc,
        )
        return evaluate_submission(submission_id)



@celery_app.task
def evaluate_submission(submission_id: int):
    logger.info(f"[WORKER] Evaluating submission {submission_id}")
    try:
        submission = Submission.objects.get(pk=submission_id)

        # --- Вызов чекера по метрике ---
        result = checker_service.check_submission(submission)

        # --- Обработка результата ---
        status = Submission.STATUS_ACCEPTED if result.ok else Submission.STATUS_FAILED
        result_outputs = dict(result.outputs or {})
        if result.ok:
            # If the checker has already persisted a rich metrics payload (dict),
            # keep existing keys and only append missing worker/checker outputs.
            if isinstance(submission.metrics, dict) and submission.metrics:
                metrics_payload = dict(submission.metrics)
                for key, value in result_outputs.items():
                    metrics_payload.setdefault(key, value)
            else:
                if isinstance(submission.metrics, (int, float)):
                    numeric_value = float(submission.metrics)
                    metrics_payload = {
                        "metric": numeric_value,
                        "metric_score": numeric_value,
                    }
                elif isinstance(submission.metrics, str):
                    metrics_payload = {"metric": submission.metrics}
                else:
                    metrics_payload = {}
                metrics_payload.update(result_outputs)
                metric_score = metrics_payload.get("metric_score")
                if isinstance(metric_score, (int, float)):
                    # Keep metric aligned with latest checker output.
                    metrics_payload["metric"] = float(metric_score)
        else:
            error_value = result.errors or "Unknown evaluation error"
            if isinstance(error_value, (list, tuple)):
                error_value = error_value[0] if error_value else "Unknown evaluation error"
            metrics_payload = {"error": str(error_value)}

        submission.status = status
        submission.metrics = metrics_payload
        submission.save(update_fields=["status", "metrics"])

        logger.info(f"[WORKER] Submission {submission_id} evaluation finished: {submission.status}")
        return {"submission_id": submission_id, "status": submission.status}

    except Submission.DoesNotExist:
        logger.error(f"[WORKER] Submission {submission_id} does not exist")
        return {"submission_id": submission_id, "status": "failed", "error": "Submission does not exist"}

    except Exception as e:
        logger.exception(f"[WORKER] Error evaluating submission {submission_id}: {str(e)}")
        if 'submission' in locals():
            submission.status = Submission.STATUS_FAILED
            submission.metrics = {"error": str(e)}
            submission.save(update_fields=["status", "metrics"])
        return {"submission_id": submission_id, "status": "error", "error": str(e)}
