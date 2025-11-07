# runner/services/metrics.py
import pandas as pd
import numpy as np
from typing import Union, List, Any
import logging
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    mean_squared_error, mean_absolute_error, r2_score,
    roc_auc_score, log_loss
)

logger = logging.getLogger(__name__)


class MetricCalculator:
    """Калькулятор метрик для оценки ML моделей"""
    
    @staticmethod
    def calculate_metric(metric_name: str, y_true: Union[List, np.ndarray, pd.Series], 
                        y_pred: Union[List, np.ndarray, pd.Series]) -> float:
        """
        Основной метод для вычисления метрики
        
        Args:
            metric_name: Название метрики
            y_true: Истинные значения
            y_pred: Предсказанные значения
            
        Returns:
            Значение метрики
        """
        metric_name = metric_name.lower().strip()
        
        # Приводим к numpy array для единообразия
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        # Словарь доступных метрик
        metrics_map = {
            # Классификационные метрики
            'accuracy': MetricCalculator._accuracy,
            'f1': MetricCalculator._f1_score,
            'f1_score': MetricCalculator._f1_score,
            'f1_macro': lambda yt, yp: f1_score(yt, yp, average='macro'),
            'f1_micro': lambda yt, yp: f1_score(yt, yp, average='micro'),
            'f1_weighted': lambda yt, yp: f1_score(yt, yp, average='weighted'),
            'precision': MetricCalculator._precision,
            'precision_score': MetricCalculator._precision,
            'precision_macro': lambda yt, yp: precision_score(yt, yp, average='macro'),
            'recall': MetricCalculator._recall,
            'recall_score': MetricCalculator._recall,
            'recall_macro': lambda yt, yp: recall_score(yt, yp, average='macro'),
            'auc_roc': MetricCalculator._auc_roc,
            'roc_auc': MetricCalculator._auc_roc,
            'log_loss': MetricCalculator._log_loss,
            
            # Регрессионные метрики
            'mse': MetricCalculator._mse,
            'mean_squared_error': MetricCalculator._mse,
            'rmse': MetricCalculator._rmse,
            'mae': MetricCalculator._mae,
            'mean_absolute_error': MetricCalculator._mae,
            'r2': MetricCalculator._r2_score,
            'r2_score': MetricCalculator._r2_score,
        }
        
        if metric_name not in metrics_map:
            logger.info(f"Unknown metric: {metric_name}. Using RMSE as default.")
            return MetricCalculator._rmse(y_true, y_pred)
        
        try:
            return metrics_map[metric_name](y_true, y_pred)
        except Exception as e:
            logger.info(f"Metric '{metric_name}' failed ({e}); falling back to default.")
            # Пробуем определить тип задачи и использовать метрику по умолчанию
            return MetricCalculator._default_metric(y_true, y_pred)
    
    @staticmethod
    def get_available_metrics() -> List[str]:
        """Возвращает список доступных метрик"""
        return [
            # Классификация
            'accuracy', 'f1', 'f1_macro', 'f1_micro', 'f1_weighted',
            'precision', 'precision_macro', 'recall', 'recall_macro',
            'auc_roc', 'log_loss',
            # Регрессия
            'mse', 'rmse', 'mae', 'r2'
        ]
    
    @staticmethod
    def _default_metric(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Метрика по умолчанию в зависимости от типа данных"""
        if MetricCalculator._is_classification(y_true):
            return MetricCalculator._accuracy(y_true, y_pred)
        else:
            return MetricCalculator._rmse(y_true, y_pred)
    
    @staticmethod
    def _is_classification(y: np.ndarray) -> bool:
        """Определяет, является ли задача классификацией"""
        return not (np.issubdtype(y.dtype, np.floating) or np.issubdtype(y.dtype, np.integer))
    
    # Классификационные метрики
    @staticmethod
    def _accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return accuracy_score(y_true, y_pred)
    
    @staticmethod
    def _f1_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return f1_score(y_true, y_pred, average='macro')
    
    @staticmethod
    def _precision(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return precision_score(y_true, y_pred, average='macro', zero_division=0)
    
    @staticmethod
    def _recall(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return recall_score(y_true, y_pred, average='macro', zero_division=0)
    
    @staticmethod
    def _auc_roc(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        # Для бинарной классификации
        if len(np.unique(y_true)) == 2:
            return roc_auc_score(y_true, y_pred)
        else:
            # Для многоклассовой - используем микро-усреднение
            return roc_auc_score(y_true, y_pred, multi_class='ovo', average='macro')
    
    @staticmethod
    def _log_loss(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return log_loss(y_true, y_pred)
    
    # Регрессионные метрики
    @staticmethod
    def _mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return mean_squared_error(y_true, y_pred)
    
    @staticmethod
    def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return np.sqrt(mean_squared_error(y_true, y_pred))
    
    @staticmethod
    def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return mean_absolute_error(y_true, y_pred)
    
    @staticmethod
    def _r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return r2_score(y_true, y_pred)


# Упрощенный интерфейс для быстрого использования
def calculate_metric(metric_name: str, y_true: Union[List, np.ndarray, pd.Series], 
                    y_pred: Union[List, np.ndarray, pd.Series]) -> float:
    """Упрощенная функция для вычисления метрики"""
    return MetricCalculator.calculate_metric(metric_name, y_true, y_pred)


def get_available_metrics() -> List[str]:
    """Получить список доступных метрик"""
    return MetricCalculator.get_available_metrics()
