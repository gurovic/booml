# runner/services/checker.py
import logging
from typing import Any, Dict, Optional

import pandas as pd

from ..models.submission import Submission
from ..models.problem_desriptor import ProblemDescriptor
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

        ground_truth_df = self._load_ground_truth(getattr(problem_data, "test_file", None))
        if ground_truth_df is None:
            return CheckResult(False, errors="Failed to load ground truth from problem data")

        metric_name = self._get_metric_name(submission)
        if not metric_name:
            return CheckResult(False, errors="Metric name not found in submission.metrics")

        metric_result = self._calculate_metric(submission_df, ground_truth_df, descriptor, metric_name)
        if not metric_result["success"]:
            return CheckResult(False, errors=metric_result.get("error", "Metric calculation failed"))

        report_data = {
            "metric": metric_result["score"],
            "file_name": getattr(getattr(submission, "file", None), "name", "submission.csv"),
            "status": "success",
            "log": f"Metric {metric_name}: {metric_result['score']:.4f}",
            "errors": "",
            "test_data": {
                "submission_id": getattr(submission, "id", None),
                "problem_id": getattr(problem, "id", None),
                "metric_used": metric_name,
            },
        }

        report = self.report_generator.create_report_from_testing_system(report_data)
        broadcast_metric_update(
            getattr(submission, "id", None),
            metric_name,
            getattr(report, "metric", metric_result["score"]),
        )
        logger.info(
            "Check completed for submission %s. Metric %s: %.4f",
            getattr(submission, "id", "?"),
            metric_name,
            metric_result["score"],
        )

        return CheckResult(
            ok=True,
            outputs={
                "report_id": getattr(report, "id", None),
                "metric_score": metric_result["score"],
                "metric_name": metric_name,
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

    def _load_ground_truth(self, file_field) -> Optional[pd.DataFrame]:
        """Загружаем ground truth из test_file ProblemData"""
        path = getattr(file_field, "path", None)
        if not path:
            logger.warning("Test file not available in ProblemData")
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

    def _calculate_metric(
        self,
        submission_df: pd.DataFrame,
        ground_truth_df: pd.DataFrame,
        descriptor: ProblemDescriptor,
        metric_name: str,
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
        score = calculate_metric(metric_name, y_true, y_pred)

        logger.info("Calculated metric '%s': %.4f for %d samples", metric_name, score, len(y_true))
        return {"success": True, "score": float(score)}


def check_submission(submission: Submission) -> CheckResult:
    """Основная функция для проверки submission (используется worker'ом)"""
    checker = SubmissionChecker()
    return checker.check_submission(submission)
