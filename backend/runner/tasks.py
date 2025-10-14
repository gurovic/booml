from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def enqueue_submission_for_evaluation(submission_id: int):
    logger.info(f"[QUEUE] Submission {submission_id} added to evaluation queue.")
    evaluate_submission.delay(submission_id)
    return {"status": "enqueued", "submission_id": submission_id}


@shared_task
def evaluate_submission(submission_id: int):
    logger.info(f"[WORKER] Evaluating submission {submission_id}")
    # здесь позже можно будет вызывать чекер
    return {"submission_id": submission_id, "status": "accepted"}
