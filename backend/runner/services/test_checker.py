import unittest
import pandas as pd
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from runner.services.checker import SubmissionChecker, check_submission, CheckResult
from runner.models import Submission, Problem
from runner.models.problem_data import ProblemData
from runner.models.problem_desriptor import ProblemDescriptor  # ИСПРАВЛЕНА ОПЕЧАТКА!
from runner.services.report_service import ReportGenerator, Report


class TestChecker(unittest.TestCase):
    def setUp(self):
        """Настройка моков для моделей Django"""
        
        # Мок для Problem
        self.mock_problem = Mock(spec=Problem)
        self.mock_problem.id = 1
        self.mock_problem.title = "Test Problem"
        
        # Мок для ProblemData
        self.mock_problem_data = Mock(spec=ProblemData)
        self.mock_problem_data.test_file = MagicMock()
        self.mock_problem_data.test_file.path = "/fake/path/test.csv"
        
        # Мок для ProblemDescriptor - ВАЖНО: используем реальные строки!
        self.mock_problem_descriptor = Mock(spec=ProblemDescriptor)
        self.mock_problem_descriptor.id_column = "id"  # СТРОКА, не мок!
        self.mock_problem_descriptor.target_column = "target"  # СТРОКА, не мок!
        self.mock_problem_descriptor.metric_name = "accuracy"
        self.mock_problem_descriptor.metric_code = ""
        
        # Мок для Submission
        self.mock_submission = Mock(spec=Submission)
        self.mock_submission.id = 1
        self.mock_submission.problem = self.mock_problem
        self.mock_submission.metrics = {}
        self.mock_submission.file = MagicMock()
        self.mock_submission.file.path = "/fake/path/submission.csv"
        self.mock_submission.save = Mock()
        
        # Связываем моки через правильные related_name
        self.mock_problem.data = self.mock_problem_data  # related_name="data"
        self.mock_problem.descriptor = self.mock_problem_descriptor  # related_name="descriptor"
        
        # Создаем тестовые данные
        self.test_data = {
            'submission': pd.DataFrame({
                'id': [1, 2, 3, 4, 5],
                'target': [0.1, 0.9, 0.2, 0.8, 0.3]
            }),
            'ground_truth': pd.DataFrame({
                'id': [1, 2, 3, 4, 5],
                'target': [0.0, 1.0, 0.0, 1.0, 0.0]
            })
        }

    def create_temp_csv(self, df, suffix=''):
        """Создает временный CSV файл и регистрирует очистку"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=f'{suffix}.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        path = temp_file.name

        def _cleanup():
            if os.path.exists(path):
                os.unlink(path)

        self.addCleanup(_cleanup)
        return path

    def tearDown(self):
        """Очистка после тестов"""
        pass

    @patch('runner.services.checker.broadcast_metric_update')
    @patch('runner.services.checker.ReportGenerator')
    @patch('runner.services.checker.pd.read_csv')
    def test_successful_check(self, mock_read_csv, mock_report_generator, mock_broadcast):
        """Тест успешной проверки submission"""
        # Настраиваем моки
        mock_read_csv.side_effect = [
            self.test_data['submission'],
            self.test_data['ground_truth']
        ]
        
        mock_report = Mock(spec=Report)
        mock_report.id = 1
        mock_report.metric = 0.76
        mock_report_generator.return_value.create_report_from_testing_system.return_value = mock_report
        
        # Создаем временные файлы
        submission_file = self.create_temp_csv(self.test_data['submission'], 'submission')
        test_file = self.create_temp_csv(self.test_data['ground_truth'], 'test')
        
        try:
            # Устанавливаем пути к файлам
            self.mock_submission.file.path = submission_file
            self.mock_problem_data.test_file.path = test_file
            
            checker = SubmissionChecker()
            result = checker.check_submission(self.mock_submission)
            
            # Проверяем результаты
            self.assertTrue(result.ok)
            self.assertIn('metric_score', result.outputs)
            self.assertIn('metric_name', result.outputs)
            self.assertEqual(result.outputs['metric_name'], 'accuracy')
            self.assertEqual(result.errors, '')
            mock_broadcast.assert_called_once_with(1, 'accuracy', 0.76)
            self.mock_submission.save.assert_called_once()
            self.assertIn('metric', self.mock_submission.metrics)
            
        finally:
            # Удаляем временные файлы
            if os.path.exists(submission_file):
                os.unlink(submission_file)
            if os.path.exists(test_file):
                os.unlink(test_file)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_missing_problem_data(self, mock_read_csv):
        """Тест проверки с отсутствующими ProblemData"""
        self.mock_problem.data = None  # Используем правильное имя поля
        
        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)
        
        self.assertFalse(result.ok)
        self.assertIn("ProblemData not found", result.errors)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_missing_problem_descriptor(self, mock_read_csv):
        """Тест проверки с отсутствующим ProblemDescriptor"""
        self.mock_problem.descriptor = None  # Используем правильное имя поля
        
        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)
        
        self.assertFalse(result.ok)
        self.assertIn("ProblemDescriptor not found", result.errors)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_missing_metric(self, mock_read_csv):
        """Тест проверки с отсутствующей метрикой"""
        self.mock_problem_descriptor.metric_name = ""
        self.mock_problem_descriptor.metric_code = ""
        
        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)
        
        self.assertFalse(result.ok)
        self.assertIn("Metric name not found for this task", result.errors)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_invalid_submission_file(self, mock_read_csv):
        """Тест проверки с невалидным файлом submission"""
        mock_read_csv.side_effect = [Exception("File error"), self.test_data['ground_truth']]
        
        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)
        
        self.assertFalse(result.ok)
        self.assertIn("Failed to load submission file", result.errors)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_invalid_test_file(self, mock_read_csv):
        """Тест проверки с невалидным test файлом"""
        mock_read_csv.side_effect = [self.test_data['submission'], Exception("File error")]
        
        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)
        
        self.assertFalse(result.ok)
        self.assertIn("Failed to load ground truth", result.errors)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_no_matching_ids(self, mock_read_csv):
        """Тест проверки с несовпадающими ID"""
        different_data = {
            'submission': pd.DataFrame({
                'id': [10, 20, 30],  # Другие ID
                'target': [0.1, 0.9, 0.2]
            }),
            'ground_truth': pd.DataFrame({
                'id': [1, 2, 3, 4, 5],  # Другие ID
                'target': [0.0, 1.0, 0.0, 1.0, 0.0]
            })
        }
        mock_read_csv.side_effect = [different_data['submission'], different_data['ground_truth']]
        
        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)
        
        self.assertFalse(result.ok)
        self.assertIn("No matching IDs", result.errors)

    def test_get_metric_name_from_dict(self):
        """Тест извлечения названия метрики из словаря"""
        checker = SubmissionChecker()
        
        # Тест с явным ключом 'metric'
        self.mock_submission.metrics = {'metric': 'accuracy'}
        metric_name = checker._get_metric_name(self.mock_submission)
        self.assertEqual(metric_name, 'accuracy')
        
        # Тест с метрикой как первым ключом
        self.mock_submission.metrics = {'f1': 0.0}
        metric_name = checker._get_metric_name(self.mock_submission)
        self.assertEqual(metric_name, 'f1')
        
        # Тест с пустым словарем
        self.mock_submission.metrics = {}
        metric_name = checker._get_metric_name(self.mock_submission)
        self.assertIsNone(metric_name)
        
        # Тест с None
        self.mock_submission.metrics = None
        metric_name = checker._get_metric_name(self.mock_submission)
        self.assertIsNone(metric_name)

    @patch('runner.services.checker.broadcast_metric_update')
    @patch('runner.services.checker.ReportGenerator')
    @patch('runner.services.checker.pd.read_csv')
    def test_check_submission_function(self, mock_read_csv, mock_report_generator, mock_broadcast):
        """Тест функции check_submission"""
        mock_read_csv.side_effect = [
            self.test_data['submission'],
            self.test_data['ground_truth']
        ]
        
        mock_report = Mock(spec=Report)
        mock_report.id = 1
        mock_report.metric = 0.91
        mock_report_generator.return_value.create_report_from_testing_system.return_value = mock_report
        
        result = check_submission(self.mock_submission)
        
        self.assertIsInstance(result, CheckResult)
        self.assertTrue(result.ok)
        mock_broadcast.assert_called_once_with(1, 'accuracy', 0.91)

    @patch('runner.services.checker.broadcast_metric_update')
    @patch('runner.services.checker.ReportGenerator')
    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_different_metric_types(self, mock_read_csv, mock_report_generator, mock_broadcast):
        """Тест с разными типами метрик"""
        test_cases = [
            ('accuracy', 0.8),
            ('f1', 0.8),
            ('mse', 0.024),
            ('rmse', 0.1549),
            ('mae', 0.12),
        ]
        
        for metric_name, expected_score in test_cases:
            with self.subTest(metric_name=metric_name):
                self.mock_problem_descriptor.metric_name = metric_name
                self.mock_problem_descriptor.metric_code = ""
                mock_read_csv.side_effect = [
                    self.test_data['submission'],
                    self.test_data['ground_truth']
                ]

                mock_report = Mock(spec=Report)
                mock_report.metric = 0.55
                mock_report_generator.return_value.create_report_from_testing_system.return_value = mock_report
                
                checker = SubmissionChecker()
                result = checker.check_submission(self.mock_submission)
                
                self.assertTrue(result.ok)
                self.assertEqual(result.outputs['metric_name'], metric_name)
                self.assertIsInstance(result.outputs['metric_score'], float)
                mock_broadcast.assert_called_once_with(1, metric_name, 0.55)
                mock_broadcast.reset_mock()

    @patch('runner.services.checker.broadcast_metric_update')
    @patch('runner.services.checker.ReportGenerator')
    @patch('runner.services.checker.pd.read_csv')
    def test_custom_metric_code_execution(self, mock_read_csv, mock_report_generator, mock_broadcast):
        mock_read_csv.side_effect = [
            self.test_data['submission'],
            self.test_data['ground_truth'],
        ]

        mock_report = Mock(spec=Report)
        mock_report.metric = 0.42
        mock_report_generator.return_value.create_report_from_testing_system.return_value = mock_report

        self.mock_problem_descriptor.metric_name = "macro_iou"
        self.mock_problem_descriptor.metric_code = (
            "def compute_metric(y_true, y_pred):\n"
            "    return {'metric': 0.5, 'macro_iou': 0.5}\n"
        )

        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)

        self.assertTrue(result.ok)
        self.assertEqual(result.outputs['metric_name'], 'macro_iou')
        self.assertIn('macro_iou', self.mock_submission.metrics)
        mock_broadcast.assert_called_once_with(1, 'macro_iou', 0.42)
