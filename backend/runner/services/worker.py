from celery import shared_task
import logging

logger = logging.getLogger(__name__)

from runner.models.submission import Submission
# from runner.services.table_checker import check_submission ПОКА ЧТО ЧЕКЕРА НЕТ

@shared_task
def enqueue_submission_for_evaluation(submission_id: int):
    logger.info(f"[QUEUE] Submission {submission_id} added to evaluation queue.")
    evaluate_submission.delay(submission_id)
    return {"status": "enqueued", "submission_id": submission_id}



@shared_task
def evaluate_submission(submission_id: int):
    logger.info(f"[WORKER] Evaluating submission {submission_id}")
    try:
        submission = Submission.objects.get(pk=submission_id)

        # --- Вызов чекера по метрике ---
        result = check_submission(submission)

        # --- Обработка результата ---
        submission.status = "checked" if result.ok else "failed"
        submission.result_outputs = result.outputs
        submission.result_errors = result.errors
        submission.save(update_fields=['status', 'result_outputs', 'result_errors'])

        logger.info(f"[WORKER] Submission {submission_id} evaluation finished: {submission.status}")
        return {"submission_id": submission_id, "status": submission.status}

    except Submission.DoesNotExist:
        logger.error(f"[WORKER] Submission {submission_id} does not exist")
        return {"submission_id": submission_id, "status": "failed", "error": "Submission does not exist"}

    except Exception as e:
        logger.exception(f"[WORKER] Error evaluating submission {submission_id}: {str(e)}")
        return {"submission_id": submission_id, "status": "error", "error": str(e)}