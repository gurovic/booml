# runner/services/checker.py
import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
from django.core.exceptions import ObjectDoesNotExist

from ..models.submission import Submission
from ..models.problem import Problem
from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor
from .report_service import ReportGenerator
from .metrics import calculate_metric

logger = logging.getLogger(__name__)


class CheckResult:
    """Результат проверки submission"""
    def __init__(self, ok: bool, outputs: Dict[str, Any] = None, errors: str = ""):
        self.ok = ok
        self.outputs = outputs or {}
        self.errors = errors


class SubmissionChecker:
    def __init__(self):
        self.report_generator = ReportGenerator()

    def check_submission(self, submission: Submission) -> CheckResult:
        """
        Основная функция проверки submission
        """
        logger.info(f"Starting check for submission {submission.id}")
        
        # 1. Получаем связанные данные напрямую из Problem
        problem = submission.problem
        
        # Получаем ProblemData и ProblemDescriptor через one-to-one связь с Task
        problem_data = problem.problem_data
        problem_descriptor = problem.problem_descriptor
        
        if not problem_data:
            return CheckResult(False, errors="ProblemData not found for this task")
            
        if not problem_descriptor:
            return CheckResult(False, errors="ProblemDescriptor not found for this task")

        # 2. Загружаем файлы
        submission_df = self._load_submission_file(submission.file)
        ground_truth_df = self._load_ground_truth(problem_data.test_file)
        
        if submission_df is None:
            return CheckResult(False, errors="Failed to load submission file")
            
        if ground_truth_df is None:
            return CheckResult(False, errors="Failed to load ground truth from problem data")

        # 3. Получаем название метрики из submission.metrics
        metric_name = self._get_metric_name(submission)
        if not metric_name:
            return CheckResult(False, errors="Metric name not found in submission.metrics")

        # 4. Сопоставляем данные и вычисляем метрику
        metric_result = self._calculate_metric(
            submission_df, 
            ground_truth_df, 
            problem_descriptor,
            metric_name
        )

        if not metric_result['success']:
            return CheckResult(False, errors=metric_result.get('error', 'Metric calculation failed'))

        # 5. Создаем отчет
        report_data = {
            'metric': metric_result['score'],
            'file_name': submission.file.name,
            'status': 'success',
            'log': f"Metric {metric_name}: {metric_result['score']:.4f}",
            'errors': '',
            'test_data': {
                'submission_id': submission.id,
                'problem_id': problem.id,
                'metric_used': metric_name
            }
        }

        report = self.report_generator.create_report_from_testing_system(report_data)
        
        logger.info(f"Check completed for submission {submission.id}. Metric {metric_name}: {metric_result['score']}")

        return CheckResult(
            ok=True,
            outputs={
                'report_id': report.id,
                'metric_score': metric_result['score'],
                'metric_name': metric_name
            }
        )

    def _load_submission_file(self, file_field) -> pd.DataFrame:
        """Загружаем файл submission"""
        if hasattr(file_field, 'path'):
            return pd.read_csv(file_field.path)
        else:
            return pd.read_csv(file_field)

    def _load_ground_truth(self, file_field) -> pd.DataFrame:
        """Загружаем ground truth из test_file ProblemData"""
        if file_field and hasattr(file_field, 'path'):
            return pd.read_csv(file_field.path)
        else:
            logger.warning("Test file not available in ProblemData")
            return None

    def _get_metric_name(self, submission: Submission) -> str:
        """
        Получаем название метрики из submission.metrics
        """
        if submission.metrics and isinstance(submission.metrics, dict):
            # Если метрика указана явно в ключе 'metric'
            if 'metric' in submission.metrics:
                return str(submission.metrics['metric'])
            # Или берем первый ключ, если это название метрики
            elif submission.metrics:
                first_key = list(submission.metrics.keys())[0]
                return str(first_key)
        
        logger.warning(f"No valid metric found in submission {submission.id} metrics: {submission.metrics}")
        return None 


    def _calculate_metric(self, submission_df: pd.DataFrame, 
                         ground_truth_df: pd.DataFrame,
                         descriptor: ProblemDescriptor,
                         metric_name: str) -> Dict[str, Any]:
        """
        Вычисление метрики качества
        """
        # Сопоставляем данные по ID колонке
        merged_df = pd.merge(
            ground_truth_df, 
            submission_df, 
            on=descriptor.id_column, 
            suffixes=('_true', '_pred')
        )

        if merged_df.empty:
            return {
                'success': False,
                'error': 'No matching IDs found between submission and ground truth',
                'score': 0.0
            }

        # Проверяем, что в ground_truth есть target колонка
        true_target_column = f"{descriptor.target_column}_true"
        pred_target_column = f"{descriptor.target_column}_pred"
        
        if true_target_column not in merged_df.columns:
            return {
                'success': False,
                'error': f'Target column "{descriptor.target_column}" not found in ground truth data',
                'score': 0.0
            }

        # Получаем настоящие значения и предсказания
        y_true = merged_df[true_target_column]
        y_pred = merged_df[pred_target_column]

        # Вычисляем метрику
        score = calculate_metric(metric_name, y_true, y_pred)

        logger.info(f"Calculated metric '{metric_name}': {score:.4f} for {len(y_true)} samples")

        return {
            'success': True,
            'score': score
        }


# Функция для импорта в worker.py
def check_submission(submission: Submission) -> CheckResult:
    """Основная функция для проверки submission"""
    checker = SubmissionChecker()
    return checker.check_submission(submission)