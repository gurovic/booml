from __future__ import annotations

import math
import statistics
import textwrap
from typing import Any, Callable, Dict

import numpy as np
import pandas as pd

from .metrics import calculate_metric


class MetricExecutionError(Exception):
    """Raised when custom metric code cannot be executed."""


SAFE_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "round": round,
    "enumerate": enumerate,
    "range": range,
    "zip": zip,
    "sorted": sorted,
    "map": map,
    "filter": filter,
    "float": float,
    "int": int,
}

SAFE_GLOBALS = {
    "np": np,
    "numpy": np,
    "pd": pd,
    "pandas": pd,
    "math": math,
    "statistics": statistics,
    "calculate_metric": calculate_metric,
}


class MetricCodeExecutor:
    """
    Executes user provided Python metric snippet in a restricted environment.

    Expected snippet:
    ```
    def compute_metric(y_true, y_pred):
        return {"metric": 0.5, "f1": 0.5}
    ```
    """

    FUNCTION_CANDIDATES = ("compute_metric", "calculate_metric", "metric", "evaluate")

    def __init__(self, source: str):
        self.source = textwrap.dedent(source or "").strip()

    def run(self, y_true, y_pred) -> Dict[str, Any]:
        if not self.source:
            raise MetricExecutionError("Metric code is empty")
        local_env: Dict[str, Any] = {}
        exec(self.source, {**SAFE_GLOBALS, "__builtins__": SAFE_BUILTINS}, local_env)
        func = self._locate_callable(local_env)
        result = func(y_true, y_pred)
        return self._normalize_result(result)

    def _locate_callable(self, namespace: Dict[str, Any]) -> Callable:
        for name in self.FUNCTION_CANDIDATES:
            candidate = namespace.get(name)
            if callable(candidate):
                return candidate
        raise MetricExecutionError("Metric code must define compute_metric(y_true, y_pred)")

    def _normalize_result(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, (tuple, list)) and len(value) == 2 and isinstance(value[0], str):
            return {value[0]: value[1]}
        if isinstance(value, (int, float)):
            return {"metric": float(value)}
        raise MetricExecutionError("Метрика должна возвращать число, словарь или пару (name, value)")
