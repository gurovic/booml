import unittest
import pandas as pd
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from .checker import SubmissionChecker, check_submission, CheckResult
from ..models.submission import Submission
from ..models.task import Task
from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor
from .report_service import ReportGenerator, Report


class TestChecker(unittest.TestCase):

    def setUp(self):
        """Настройка моков для моделей Django"""
        
        # Мок для Task
        self.mock_task = Mock(spec=Task)
        self.mock_task.id = 1
        self.mock_task.title = "Test Task"
        
        # Мок для ProblemData
        self.mock_problem_data = Mock(spec=ProblemData)
        self.mock_problem_data.test_file = None
        
        # Мок для ProblemDescriptor
        self.mock_problem_descriptor = Mock(spec=ProblemDescriptor)
        self.mock_problem_descriptor.id_column = "id"
        self.mock_problem_descriptor.target_column = "target"
        self.mock_problem_descriptor.id_type = "int"
        self.mock_problem_descriptor.target_type = "float"
        
        # Мок для Submission
        self.mock_submission = Mock(spec=Submission)
        self.mock_submission.id = 1
        self.mock_submission.task = self.mock_task
        self.mock_submission.metrics = {"accuracy": 0.0}
        self.mock_submission.file = None
        
        # Связываем моки
        self.mock_task.problemdata = self.mock_problem_data
        self.mock_task.problemdescriptor = self.mock_problem_descriptor
        
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
        """Создает временный CSV файл"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=f'{suffix}.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        return temp_file.name

    def tearDown(self):
        """Очистка после тестов"""
        pass

    @patch('runner.services.checker.ReportGenerator')
    @patch('runner.services.checker.pd.read_csv')
    def test_successful_check(self, mock_read_csv, mock_report_generator):
        """Тест успешной проверки submission"""
        # Настраиваем моки
        mock_read_csv.side_effect = [
            self.test_data['submission'],
            self.test_data['ground_truth']
        ]
        
        mock_report = Mock(spec=Report)
        mock_report.id = 1
        mock_report_generator.return_value.create_report_from_testing_system.return_value = mock_report
        
        # Создаем временные файлы
        submission_file = self.create_temp_csv(self.test_data['submission'], 'submission')
        test_file = self.create_temp_csv(self.test_data['ground_truth'], 'test')
        
        try:
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
            
        finally:
            # Удаляем временные файлы
            if os.path.exists(submission_file):
                os.unlink(submission_file)
            if os.path.exists(test_file):
                os.unlink(test_file)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_missing_problem_data(self, mock_read_csv):
        """Тест проверки с отсутствующими ProblemData"""
        self.mock_task.problemdata = None
        
        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)
        
        self.assertFalse(result.ok)
        self.assertIn("ProblemData not found", result.errors)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_missing_problem_descriptor(self, mock_read_csv):
        """Тест проверки с отсутствующим ProblemDescriptor"""
        self.mock_task.problemdescriptor = None
        
        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)
        
        self.assertFalse(result.ok)
        self.assertIn("ProblemDescriptor not found", result.errors)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_missing_metric(self, mock_read_csv):
        """Тест проверки с отсутствующей метрикой"""
        self.mock_submission.metrics = {}
        
        checker = SubmissionChecker()
        result = checker.check_submission(self.mock_submission)
        
        self.assertFalse(result.ok)
        self.assertIn("Metric name not found", result.errors)

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
            'ground_truth': self.test_data['ground_truth']
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

    @patch('runner.services.checker.ReportGenerator')
    @patch('runner.services.checker.pd.read_csv')
    def test_check_submission_function(self, mock_read_csv, mock_report_generator):
        """Тест функции check_submission"""
        mock_read_csv.side_effect = [
            self.test_data['submission'],
            self.test_data['ground_truth']
        ]
        
        mock_report = Mock(spec=Report)
        mock_report.id = 1
        mock_report_generator.return_value.create_report_from_testing_system.return_value = mock_report
        
        result = check_submission(self.mock_submission)
        
        self.assertIsInstance(result, CheckResult)
        self.assertTrue(result.ok)

    @patch('runner.services.checker.pd.read_csv')
    def test_check_with_different_metric_types(self, mock_read_csv):
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
                self.mock_submission.metrics = {metric_name: 0.0}
                mock_read_csv.side_effect = [
                    self.test_data['submission'],
                    self.test_data['ground_truth']
                ]
                
                checker = SubmissionChecker()
                result = checker.check_submission(self.mock_submission)
                
                self.assertTrue(result.ok)
                self.assertEqual(result.outputs['metric_name'], metric_name)
                self.assertIsInstance(result.outputs['metric_score'], float)


if __name__ == '__main__':
    unittest.main()