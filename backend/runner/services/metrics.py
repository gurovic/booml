# runner/services/metrics.py
from __future__ import annotations

import logging
from typing import Union, List

import numpy as np
import pandas as pd

try:
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        mean_squared_error,
        mean_absolute_error,
        r2_score,
        roc_auc_score,
        log_loss,
    )
    _SKLEARN_AVAILABLE = True
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    _SKLEARN_AVAILABLE = False

    def _ensure_array(values):
        arr = np.asarray(values)
        if arr.ndim > 1:
            arr = arr.reshape(-1)
        return arr

    def accuracy_score(y_true, y_pred):
        y_true = _ensure_array(y_true)
        y_pred = _ensure_array(y_pred)
        if y_true.size == 0:
            return 0.0
        return float(np.mean(y_true == y_pred))

    def mean_squared_error(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        if y_true.size == 0:
            return 0.0
        diff = y_true - y_pred
        return float(np.mean(diff * diff))

    def mean_absolute_error(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        if y_true.size == 0:
            return 0.0
        return float(np.mean(np.abs(y_true - y_pred)))

    def r2_score(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        if y_true.size == 0:
            return 0.0
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        if ss_tot == 0:
            return 0.0
        return float(1 - ss_res / ss_tot)

    def _classification_stats(y_true, y_pred):
        y_true = _ensure_array(y_true)
        y_pred = _ensure_array(y_pred)
        labels = np.unique(np.concatenate((y_true, y_pred))) if y_true.size or y_pred.size else np.array([])
        stats = []
        for label in labels:
            mask_pred = y_pred == label
            mask_true = y_true == label
            tp = int(np.sum(mask_true & mask_pred))
            fp = int(np.sum(~mask_true & mask_pred))
            fn = int(np.sum(mask_true & ~mask_pred))
            stats.append((label, tp, fp, fn))
        return labels, stats

    def precision_score(y_true, y_pred, average="macro", zero_division=0):
        labels, stats = _classification_stats(y_true, y_pred)
        if not stats:
            return 0.0
        per_label = []
        tp_total = fp_total = 0
        for _, tp, fp, _ in stats:
            tp_total += tp
            fp_total += fp
            denom = tp + fp
            per_label.append(tp / denom if denom else zero_division)
        if average == "micro":
            denom = tp_total + fp_total
            return float(tp_total / denom) if denom else float(zero_division)
        return float(np.mean(per_label))

    def recall_score(y_true, y_pred, average="macro", zero_division=0):
        labels, stats = _classification_stats(y_true, y_pred)
        if not stats:
            return 0.0
        per_label = []
        tp_total = fn_total = 0
        for _, tp, _, fn in stats:
            tp_total += tp
            fn_total += fn
            denom = tp + fn
            per_label.append(tp / denom if denom else zero_division)
        if average == "micro":
            denom = tp_total + fn_total
            return float(tp_total / denom) if denom else float(zero_division)
        return float(np.mean(per_label))

    def f1_score(y_true, y_pred, average="macro"):
        labels, stats = _classification_stats(y_true, y_pred)
        if not stats:
            return 0.0
        per_label = []
        tp_total = fp_total = fn_total = 0
        for _, tp, fp, fn in stats:
            tp_total += tp
            fp_total += fp
            fn_total += fn
            denom = 2 * tp + fp + fn
            per_label.append((2 * tp) / denom if denom else 0.0)
        if average == "micro":
            denom = 2 * tp_total + fp_total + fn_total
            return float((2 * tp_total) / denom) if denom else 0.0
        return float(np.mean(per_label))

    def _rankdata(values: np.ndarray) -> np.ndarray:
        order = np.argsort(values)
        ranks = np.empty_like(order, dtype=float)
        sorted_vals = values[order]
        unique_vals, inverse, counts = np.unique(sorted_vals, return_inverse=True, return_counts=True)
        cumulative = np.cumsum(counts)
        start = cumulative - counts + 1
        avg = (start + cumulative) / 2.0
        ranks_sorted = avg[inverse]
        ranks[order] = ranks_sorted
        return ranks

    def roc_auc_score(y_true, y_score, multi_class=None, average="macro"):
        y_true = _ensure_array(y_true)
        y_score = np.asarray(y_score, dtype=float)
        labels = np.unique(y_true)
        if labels.size != 2:
            raise RuntimeError("Fallback roc_auc_score поддерживает только бинарные задачи.")
        pos_label = labels[-1]
        binary_true = (y_true == pos_label).astype(int)
        if y_score.ndim == 2:
            if y_score.shape[1] != labels.size:
                raise RuntimeError("Матрица вероятностей не соответствует количеству классов.")
            pos_index = list(labels).index(pos_label)
            y_score = y_score[:, pos_index]
        ranks = _rankdata(y_score)
        n_pos = binary_true.sum()
        n_neg = binary_true.size - n_pos
        if n_pos == 0 or n_neg == 0:
            return 0.5
        auc = (ranks[binary_true == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
        return float(auc)

    def log_loss(y_true, y_pred, eps=1e-15):
        y_true = _ensure_array(y_true)
        y_pred = np.asarray(y_pred, dtype=float)
        if y_pred.ndim == 1:
            labels = np.unique(y_true)
            if labels.size != 2:
                raise RuntimeError("Для бинарного log_loss требуется два класса.")
            pos_label = labels[-1]
            y_true_bin = (y_true == pos_label).astype(float)
            probs = np.clip(y_pred, eps, 1 - eps)
            return float(-np.mean(y_true_bin * np.log(probs) + (1 - y_true_bin) * np.log(1 - probs)))
        elif y_pred.ndim == 2:
            labels = np.unique(y_true)
            if y_pred.shape[1] != labels.size:
                raise RuntimeError("Число столбцов вероятностей должно совпадать с числом классов.")
            probs = np.clip(y_pred, eps, 1 - eps)
            probs = probs / probs.sum(axis=1, keepdims=True)
            label_to_idx = {label: idx for idx, label in enumerate(labels)}
            indices = np.array([label_to_idx.get(label, -1) for label in y_true])
            if np.any(indices < 0):
                raise RuntimeError("Не удалось сопоставить некоторые классы в log_loss.")
            rows = np.arange(len(y_true))
            return float(-np.mean(np.log(probs[rows, indices])))
        raise RuntimeError("Неподдерживаемый формат входных данных для log_loss.")


logger = logging.getLogger(__name__)

if not _SKLEARN_AVAILABLE:
    logger.warning(
        "scikit-learn не установлен или несовместим с текущим интерпретатором. "
        "Используются упрощённые реализации метрик."
    )


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
            'exact_match': MetricCalculator._exact_match,
            'csv_match': MetricCalculator._exact_match,
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
            'mse', 'rmse', 'mae', 'r2',
            # Exact match
            'exact_match', 'csv_match',
        ]

    @staticmethod
    def _exact_match(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        y_true_arr = np.asarray(y_true)
        y_pred_arr = np.asarray(y_pred)
        if y_true_arr.shape != y_pred_arr.shape:
            return 0.0
        return float(np.array_equal(y_true_arr, y_pred_arr))
    
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
