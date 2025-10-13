from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def enqueue_submission_for_evaluation(submission_id: int):
    """
    Заглушка: задача, сигнализирующая, что сабмишн поставлен в очередь.
    Пока что она не делает саму проверку — только логирует/отмечает факт.
    """
    logger.info(f"[QUEUE] Submission {submission_id} added to evaluation queue.")
    # при дальнейшем развитии сюда можно добавить логику передачи задания в real evaluator
    return {"status": "enqueued", "submission_id": submission_id}