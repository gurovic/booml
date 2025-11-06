import unittest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from runner.services.metrics import MetricCalculator, calculate_metric


class TestMetrics(unittest.TestCase):

    def setUp(self):
        """Настройка тестовых данных"""
        self.y_true_class = [0, 1, 0, 1, 0]
        self.y_pred_class = [0, 1, 0, 1, 1]  # одна ошибка
        self.y_true_reg = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.y_pred_reg = [1.1, 2.1, 2.9, 4.2, 4.8]

    def test_accuracy_metric(self):
        """Тест метрики accuracy"""
        result = calculate_metric('accuracy', self.y_true_class, self.y_pred_class)
        expected = 0.8  # 4 правильных из 5
        self.assertAlmostEqual(result, expected, places=4)

    def test_f1_metric(self):
        """Тест метрики F1"""
        result = calculate_metric('f1', self.y_true_class, self.y_pred_class)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

    def test_mse_metric(self):
        """Тест метрики MSE"""
        result = calculate_metric('mse', self.y_true_reg, self.y_pred_reg)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)

    def test_rmse_metric(self):
        """Тест метрики RMSE"""
        result = calculate_metric('rmse', self.y_true_reg, self.y_pred_reg)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)

    def test_mae_metric(self):
        """Тест метрики MAE"""
        result = calculate_metric('mae', self.y_true_reg, self.y_pred_reg)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)

    def test_r2_metric(self):
        """Тест метрики R2"""
        result = calculate_metric('r2', self.y_true_reg, self.y_pred_reg)
        self.assertIsInstance(result, float)
        self.assertLessEqual(result, 1.0)

    def test_unknown_metric_defaults_to_rmse(self):
        """Тест неизвестной метрики (должна использоваться RMSE по умолчанию)"""
        result = calculate_metric('unknown_metric', self.y_true_reg, self.y_pred_reg)
        self.assertIsInstance(result, float)

    def test_precision_metric(self):
        """Тест метрики precision"""
        result = calculate_metric('precision', self.y_true_class, self.y_pred_class)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

    def test_recall_metric(self):
        """Тест метрики recall"""
        result = calculate_metric('recall', self.y_true_class, self.y_pred_class)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

    def test_metric_with_numpy_arrays(self):
        """Тест с numpy массивами"""
        y_true_np = np.array(self.y_true_class)
        y_pred_np = np.array(self.y_pred_class)
        result = calculate_metric('accuracy', y_true_np, y_pred_np)
        self.assertAlmostEqual(result, 0.8, places=4)

    def test_metric_with_pandas_series(self):
        """Тест с pandas Series"""
        y_true_series = pd.Series(self.y_true_class)
        y_pred_series = pd.Series(self.y_pred_class)
        result = calculate_metric('accuracy', y_true_series, y_pred_series)
        self.assertAlmostEqual(result, 0.8, places=4)

    def test_get_available_metrics(self):
        """Тест получения списка доступных метрик"""
        metrics = MetricCalculator.get_available_metrics()
        self.assertIsInstance(metrics, list)
        self.assertIn('accuracy', metrics)
        self.assertIn('f1', metrics)
        self.assertIn('mse', metrics)
        self.assertIn('rmse', metrics)

    def test_perfect_classification(self):
        """Тест идеальной классификации"""
        y_true = [0, 1, 0, 1]
        y_pred = [0, 1, 0, 1]
        result = calculate_metric('accuracy', y_true, y_pred)
        self.assertEqual(result, 1.0)

    def test_perfect_regression(self):
        """Тест идеальной регрессии"""
        y_true = [1.0, 2.0, 3.0]
        y_pred = [1.0, 2.0, 3.0]
        result = calculate_metric('mse', y_true, y_pred)
        self.assertEqual(result, 0.0)