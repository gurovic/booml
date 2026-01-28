# runner/services/checker.py
import logging
from typing import Any, Dict, Optional

import pandas as pd

from ..models.submission import Submission
from ..models.problem_desriptor import ProblemDescriptor
from .custom_metric import MetricCodeExecutor, MetricExecutionError
from .metrics import calculate_metric
from .report_service import ReportGenerator
from .websocket_notifications import broadcast_metric_update

logger = logging.getLogger(__name__)


class CheckResult:
    """Результат проверки submission"""

    def __init__(self, ok: bool, outputs: Optional[Dict[str, Any]] = None, errors: str = ""):
        self.ok = ok
        self.outputs = outputs or {}
        self.errors = errors


class SubmissionChecker:
    CSV_MATCH_METRICS = {"csv_match", "exact_match"}
    CSV_MATCH_RTOL = 1e-6
    CSV_MATCH_ATOL = 1e-8

    def __init__(self, report_generator: Optional[ReportGenerator] = None):
        self.report_generator = report_generator or ReportGenerator()

    def check_submission(self, submission: Submission) -> CheckResult:
        """
        Основная функция проверки submission
        """
        logger.info("Starting check for submission %s", getattr(submission, "id", "?"))

        problem = getattr(submission, "problem", None)
        if problem is None:
            return CheckResult(False, errors="Problem not found for this submission")

        problem_data = getattr(problem, "data", None)
        descriptor = getattr(problem, "descriptor", None)
        if not problem_data:
            return CheckResult(False, errors="ProblemData not found for this task")
        if not descriptor:
            return CheckResult(False, errors="ProblemDescriptor not found for this task")

        submission_df = self._load_submission_file(submission.file)
        if submission_df is None:
            return CheckResult(False, errors="Failed to load submission file")

        ground_truth_file = self._select_ground_truth_file(problem_data)
        ground_truth_df = self._load_ground_truth(ground_truth_file)
        if ground_truth_df is None:
            return CheckResult(False, errors="Failed to load ground truth from problem data")

        metric_name, metric_code = self._metric_config(submission, descriptor)
        if not metric_name and not metric_code:
            return CheckResult(False, errors="Metric name not found for this task")

        if self._use_csv_match(metric_name, metric_code):
            metric_result = self._calculate_csv_match(
                submission_df,
                ground_truth_df,
                descriptor,
                metric_name,
            )
        else:
            metric_result = self._calculate_metric(
                submission_df,
                ground_truth_df,
                descriptor,
                metric_name,
                metric_code,
            )
        if not metric_result["success"]:
            return CheckResult(False, errors=metric_result.get("error", "Metric calculation failed"))

        metrics_payload = metric_result.get("metrics")
        if metrics_payload is not None:
            submission.metrics = metrics_payload
            submission.save(update_fields=["metrics"])

        metric_for_log = metric_result.get("metric_name", metric_name)
        report_data = {
            "metric": metric_result["score"],
            "file_name": getattr(getattr(submission, "file", None), "name", "submission.csv"),
            "status": "success",
            "log": f"Metric {metric_for_log}: {metric_result['score']:.4f}",
            "errors": "",
            "test_data": {
                "submission_id": getattr(submission, "id", None),
                "problem_id": getattr(problem, "id", None),
                "metric_used": metric_for_log,
            },
        }

        report = self.report_generator.create_report_from_testing_system(report_data)
        if hasattr(report, "metric"):
            metric_to_broadcast = report.metric
        else:
            logger.error("Report object missing 'metric' attribute for submission %s. Using metric_result['score'] as fallback.", getattr(submission, "id", "?"))
            metric_to_broadcast = metric_result["score"]

        broadcast_metric_update(getattr(submission, "id", None), metric_for_log, metric_to_broadcast)
        
        logger.info(
            "Check completed for submission %s. Metric %s: %.4f",
            getattr(submission, "id", "?"),
            metric_for_log,
            metric_result["score"],
        )

        return CheckResult(
            ok=True,
            outputs={
                "report_id": getattr(report, "id", None),
                "metric_score": metric_result["score"],
                "metric_name": metric_for_log,
            },
        )

    def _load_submission_file(self, file_field) -> Optional[pd.DataFrame]:
        """Загружаем файл submission"""
        path = getattr(file_field, "path", None) or getattr(file_field, "name", None) or file_field
        try:
            return pd.read_csv(path)
        except Exception:  # pragma: no cover - log for observability
            logger.info("Failed to load submission file %s", path)
            return None

    def _select_ground_truth_file(self, problem_data):
        """Возвращает файл с правильными ответами (answer_file -> test_file fallback)."""
        for attr in ("answer_file", "test_file"):
            file_field = getattr(problem_data, attr, None)
            file_name = getattr(file_field, "name", "")
            if file_field and file_name:
                return file_field
        logger.warning("No answer/test files available for problem %s", getattr(problem_data, "problem_id", "?"))
        return None

    def _load_ground_truth(self, file_field) -> Optional[pd.DataFrame]:
        """Загружаем ground truth из ProblemData"""
        if not file_field:
            return None
        path = getattr(file_field, "path", None)
        if not path:
            logger.warning("Ground truth file has no path (maybe not saved yet)")
            return None
        try:
            return pd.read_csv(path)
        except Exception:  # pragma: no cover - log for observability
            logger.info("Failed to load ground truth file %s", path)
            return None

    def _get_metric_name(self, submission) -> Optional[str]:
        """Извлекает название метрики из submission.metrics"""
        metrics = getattr(submission, "metrics", None)
        if not metrics:
            return None

        if isinstance(metrics, dict):
            metric_from_field = metrics.get("metric")
            if isinstance(metric_from_field, str):
                return metric_from_field
            for key in metrics.keys():
                if isinstance(key, str):
                    return key

        if isinstance(metrics, str):
            return metrics

        return None

    def _resolve_metric_name(self, submission, descriptor: ProblemDescriptor) -> Optional[str]:
        """Находит подходящую метрику из submission.metrics, descriptor.metric или по типу таргета."""
        metric_name = self._get_metric_name(submission)
        if metric_name:
            return metric_name

        descriptor_metric = getattr(descriptor, "metric", None)
        if isinstance(descriptor_metric, str):
            descriptor_metric = descriptor_metric.strip()
            if descriptor_metric:
                return descriptor_metric

        return self._guess_metric_from_descriptor(descriptor)

    def _guess_metric_from_descriptor(self, descriptor: ProblemDescriptor) -> str:
        """Автоматический выбор метрики по типу таргета."""
        target_type = (getattr(descriptor, "target_type", "") or "").lower()
        if target_type == "float":
            return "rmse"
        if target_type in {"int", "str"}:
            return "accuracy"
        return "rmse"

    def _calculate_metric(
        self,
        submission_df: pd.DataFrame,
        ground_truth_df: pd.DataFrame,
        descriptor: ProblemDescriptor,
        metric_name: Optional[str],
        metric_code: str,
    ) -> Dict[str, Any]:
        """
        Вычисление метрики качества
        """
        merged_df = pd.merge(
            ground_truth_df,
            submission_df,
            on=descriptor.id_column,
            suffixes=("_true", "_pred"),
        )

        if merged_df.empty:
            return {
                "success": False,
                "error": "No matching IDs found between submission and ground truth",
                "score": 0.0,
            }

        target_column = descriptor.target_column
        true_target_column = f"{target_column}_true"
        pred_target_column = f"{target_column}_pred"

        if true_target_column not in merged_df.columns or pred_target_column not in merged_df.columns:
            return {
                "success": False,
                "error": f'Target column "{target_column}" not found in ground truth data',
                "score": 0.0,
            }

        y_true = merged_df[true_target_column]
        y_pred = merged_df[pred_target_column]

        try:
            metrics_payload, score = self._evaluate_metric(y_true, y_pred, metric_name, metric_code)
        except (MetricExecutionError, ValueError) as exc:
            return {"success": False, "error": str(exc), "score": 0.0}
        except Exception as exc:  # pragma: no cover - safety net for unexpected errors
            logger.exception("Metric calculation failed: %s", exc)
            return {"success": False, "error": "Metric calculation failed", "score": 0.0}

        logger.info("Calculated metric '%s': %.4f for %d samples", metric_name or "metric", score, len(y_true))
        return {
            "success": True,
            "score": float(score),
            "metrics": metrics_payload,
            "metric_name": metric_name or "metric",
        }

    def _use_csv_match(self, metric_name: Optional[str], metric_code: str) -> bool:
        if metric_code and metric_code.strip():
            return False
        if not metric_name:
            return False
        return metric_name.strip().lower() in self.CSV_MATCH_METRICS

    def _calculate_csv_match(
        self,
        submission_df: pd.DataFrame,
        ground_truth_df: pd.DataFrame,
        descriptor: ProblemDescriptor,
        metric_name: Optional[str],
    ) -> Dict[str, Any]:
        expected_columns = list(ground_truth_df.columns)
        submission_columns = list(submission_df.columns)
        missing = [col for col in expected_columns if col not in submission_columns]
        extra = [col for col in submission_columns if col not in expected_columns]
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing columns: {', '.join(missing)}")
            if extra:
                details.append(f"unexpected columns: {', '.join(extra)}")
            suffix = f" ({'; '.join(details)})" if details else ""
            return {
                "success": False,
                "error": f"Submission columns do not match answer columns{suffix}",
                "score": 0.0,
            }

        submission_df = submission_df[expected_columns]

        expected_rows = len(ground_truth_df)
        submitted_rows = len(submission_df)
        if expected_rows != submitted_rows:
            return {
                "success": False,
                "error": (
                    "Row count mismatch between submission and answer: "
                    f"expected {expected_rows}, got {submitted_rows}"
                ),
                "score": 0.0,
            }

        id_column = getattr(descriptor, "id_column", None)
        if id_column and id_column in expected_columns:
            expected_counts = ground_truth_df[id_column].value_counts(dropna=False).sort_index()
            submitted_counts = submission_df[id_column].value_counts(dropna=False).sort_index()
            if not expected_counts.equals(submitted_counts):
                return {
                    "success": False,
                    "error": f"ID column '{id_column}' values do not match answer",
                    "score": 0.0,
                }

        check_order = bool(getattr(descriptor, "check_order", False))
        if not check_order and id_column and id_column in expected_columns:
            submission_df = submission_df.sort_values(by=id_column, kind="mergesort")
            ground_truth_df = ground_truth_df.sort_values(by=id_column, kind="mergesort")

        submission_df = submission_df.reset_index(drop=True)
        ground_truth_df = ground_truth_df.reset_index(drop=True)

        matched = self._frames_match(submission_df, ground_truth_df)
        score = 1.0 if matched else 0.0
        metrics = {"metric": score}
        if metric_name:
            metrics[metric_name] = score

        return {
            "success": True,
            "score": score,
            "metrics": metrics,
            "metric_name": metric_name or "csv_match",
        }

    def _frames_match(self, left: pd.DataFrame, right: pd.DataFrame) -> bool:
        try:
            pd.testing.assert_frame_equal(
                left,
                right,
                check_dtype=False,
                check_exact=False,
                rtol=self.CSV_MATCH_RTOL,
                atol=self.CSV_MATCH_ATOL,
            )
        except AssertionError:
            return False
        return True

    def _evaluate_metric(self, y_true, y_pred, metric_name: Optional[str], metric_code: str):
        if metric_code.strip():
            executor = MetricCodeExecutor(metric_code)
            metrics = executor.run(y_true, y_pred)
        else:
            metric_id = metric_name or "rmse"
            score = calculate_metric(metric_id, y_true, y_pred)
            metrics = {"metric": float(score), metric_id: float(score)}
        metrics = self._sanitize_metrics(metrics)
        score_value = self._extract_score(metrics, preferred_key=metric_name)
        if "metric" not in metrics:
            metrics["metric"] = score_value
        if metric_name and metric_name not in metrics:
            metrics[metric_name] = score_value
        return metrics, score_value

    def _sanitize_metrics(self, metrics: Any) -> Dict[str, Any]:
        if isinstance(metrics, dict):
            sanitized: Dict[str, Any] = {}
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    sanitized[key] = float(value)
                else:
                    sanitized[key] = value
            return sanitized
        if isinstance(metrics, (int, float)):
            return {"metric": float(metrics)}
        raise ValueError("Metric code must return число или словарь")

    def _extract_score(self, metrics: Dict[str, Any], preferred_key: Optional[str] = None) -> float:
        if preferred_key and isinstance(metrics, dict):
            value = metrics.get(preferred_key)
            if isinstance(value, (int, float)):
                return float(value)
        if isinstance(metrics, dict):
            for key in ("metric", "score", "accuracy", "f1", "auc"):
                value = metrics.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
            for value in metrics.values():
                if isinstance(value, (int, float)):
                    return float(value)
        if isinstance(metrics, (int, float)):
            return float(metrics)
        raise ValueError("Cannot extract numeric metric from metric result")

    def _metric_config(self, submission, descriptor) -> tuple[Optional[str], str]:
        descriptor_metric_name = (getattr(descriptor, "metric_name", "") or "").strip()
        descriptor_metric_code = getattr(descriptor, "metric_code", "") or ""
        if descriptor_metric_code.strip():
            return descriptor_metric_name or "custom_metric", descriptor_metric_code
        if descriptor_metric_name:
            return descriptor_metric_name, ""
        legacy_name = self._get_metric_name(submission)
        return legacy_name, ""


def check_submission(submission: Submission) -> CheckResult:
    """Основная функция для проверки submission (используется worker'ом)"""
    checker = SubmissionChecker()
    return checker.check_submission(submission)
