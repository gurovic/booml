import csv
import logging
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Union

from django.db import transaction

from ..models import Submission
from .report_service import ReportGenerator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckerResult:
    ok: bool
    outputs: List[Dict[str, Any]]
    errors: List[Dict[str, str]]
    metrics: Dict[str, Any]


def check_submission(submission_or_id: Union[Submission, int]) -> CheckerResult:
    submission = _resolve_submission(submission_or_id)
    if submission is None:
        message = "Submission not found"
        logger.error(message)
        return CheckerResult(
            ok=False,
            outputs=[],
            errors=[{"code": "not_found", "message": message}],
            metrics={},
        )

    outputs: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    metrics: Dict[str, Any] = {}
    log_lines: List[str] = [f"Проверка посылки #{submission.id}"]

    try:
        predictions = _read_predictions(submission)
        metric_value, variance_value = _compute_metric(predictions)

        metrics = {
            "score": metric_value,
            "prediction_count": len(predictions),
            "variance": variance_value,
        }

        log_lines.extend(
            [
                f"Прочитано строк с прогнозами: {len(predictions)}",
                f"Дисперсия прогнозов: {variance_value}",
                f"Полученная метрика (score): {metric_value}",
            ]
        )

        outputs.append(
            {
                "type": "text",
                "data": {
                    "text": "\n".join(log_lines),
                },
            }
        )

        _store_submission_metrics(submission, metrics)
        status = Submission.STATUS_ACCEPTED
        ok = True

    except Exception as exc:  # noqa: BLE001
        ok = False
        message = str(exc) or exc.__class__.__name__
        logger.exception("Ошибка проверки посылки #%s: %s", submission.id, message)
        errors.append({"code": "checker_error", "message": message})
        log_lines.append(f"Ошибка проверки: {message}")
        _store_submission_metrics(submission, None)
        status = Submission.STATUS_FAILED
        metrics = {}

    _create_report(submission, status, metrics, errors, log_lines)

    if not ok:
        logger.info("Проверка посылки #%s завершена с ошибкой", submission.id)
    else:
        logger.info("Проверка посылки #%s успешно завершена", submission.id)

    return CheckerResult(ok=ok, outputs=outputs, errors=errors, metrics=metrics)


def _resolve_submission(submission_or_id: Union[Submission, int]) -> Submission | None:
    if isinstance(submission_or_id, Submission):
        return submission_or_id

    try:
        return Submission.objects.select_related("task").get(pk=submission_or_id)
    except Submission.DoesNotExist:
        return None


def _read_predictions(submission: Submission) -> Sequence[float]:
    if not submission.file:
        raise FileNotFoundError("У посылки отсутствует файл с предсказаниями")

    submission.file.open(mode="r", encoding="utf-8")
    try:
        reader = csv.DictReader(submission.file)
        if not reader.fieldnames or "prediction" not in reader.fieldnames:
            raise ValueError("CSV должен содержать колонку 'prediction'")

        predictions: List[float] = []
        for row_index, row in enumerate(reader, start=1):
            raw_value = row.get("prediction")
            if raw_value in (None, ""):
                raise ValueError(f"Пустое значение prediction в строке {row_index}")
            try:
                predictions.append(float(raw_value))
            except ValueError as exc:
                raise ValueError(f"Некорректное число в колонке prediction (строка {row_index})") from exc

        if not predictions:
            raise ValueError("Файл не содержит значений в колонке 'prediction'")

        return predictions
    finally:
        submission.file.close()


def _compute_metric(predictions: Iterable[float]) -> tuple[float, float]:
    predictions_list = list(predictions)
    if len(predictions_list) > 1:
        variance = statistics.pvariance(predictions_list)
    else:
        variance = 0.0

    score = 1.0 / (1.0 + variance)
    score = max(0.0, min(1.0, round(score, 6)))
    variance = round(variance, 6)
    return score, variance


def _store_submission_metrics(submission: Submission, metrics: Dict[str, Any] | None) -> None:
    desired_value = metrics or None
    if submission.metrics == desired_value:
        return
    submission.metrics = desired_value
    with transaction.atomic():
        submission.save(update_fields=["metrics"])


def _create_report(
    submission: Submission,
    status: str,
    metrics: Dict[str, Any],
    errors: Iterable[Dict[str, str]],
    log_lines: Iterable[str],
) -> None:
    file_name = Path(submission.file.name).name if submission.file else ""
    report_payload = {
        "metric": metrics.get("score", 0.0),
        "file_name": file_name,
        "status": status,
        "log": "\n".join(log_lines),
        "errors": "\n".join(err["message"] for err in errors) if errors else "",
        "test_data": {"task_id": submission.task_id, "submission_id": submission.id},
    }

    try:
        ReportGenerator().create_report_from_testing_system(report_payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Не удалось создать отчёт для посылки #%s: %s", submission.id, exc)
