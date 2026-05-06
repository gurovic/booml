from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional


MINIMIZE_METRICS = {
    "mse",
    "rmse",
    "mae",
    "mape",
    "smape",
    "msle",
    "rmsle",
    "logloss",
    "log_loss",
    "loss",
    "error",
}

MAXIMIZE_METRICS = {
    "accuracy",
    "f1",
    "f1_score",
    "f1_macro",
    "f1_micro",
    "f1_weighted",
    "precision",
    "precision_score",
    "precision_macro",
    "recall",
    "recall_score",
    "recall_macro",
    "auc",
    "auc_roc",
    "roc_auc",
    "r2",
    "r2_score",
    "exact_match",
    "csv_match",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class ScoreSpec:
    direction: str
    ideal: float
    metric_name: str


def resolve_score_spec(
    metric_name: str,
    *,
    descriptor_direction: str | None = None,
    descriptor_ideal: float | None = None,
) -> ScoreSpec:
    metric = (metric_name or "metric").strip().lower()
    manual_direction = (descriptor_direction or "").strip().lower()
    manual_ideal = _to_float(descriptor_ideal)
    if manual_direction in {"maximize", "minimize"} and manual_ideal is not None:
        return ScoreSpec(direction=manual_direction, ideal=manual_ideal, metric_name=metric)

    if metric in MINIMIZE_METRICS or any(token in metric for token in ("loss", "error", "rmse", "mse", "mae")):
        return ScoreSpec(direction="minimize", ideal=0.0, metric_name=metric)
    if metric in MAXIMIZE_METRICS:
        return ScoreSpec(direction="maximize", ideal=1.0, metric_name=metric)
    return ScoreSpec(direction="maximize", ideal=1.0, metric_name=metric)


def default_curve_p(direction: str) -> float:
    return 3.0 if direction == "minimize" else 2.0


def default_linear_reference(metric_name: str, direction: str, ideal: float) -> float:
    metric = (metric_name or "").strip().lower()
    if direction == "maximize":
        if metric in {"r2", "r2_score"}:
            return 0.0
        return 0.0
    return ideal + 1.0


def normalize_quality(raw_metric: float, *, ideal: float, reference: float, direction: str) -> float:
    raw_value = float(raw_metric)
    ideal_value = float(ideal)
    reference_value = float(reference)

    if direction == "maximize":
        denom = ideal_value - reference_value
        if abs(denom) < 1e-12:
            return 1.0 if raw_value >= ideal_value else 0.0
        q = (raw_value - reference_value) / denom
    else:
        denom = reference_value - ideal_value
        if abs(denom) < 1e-12:
            return 1.0 if raw_value <= ideal_value else 0.0
        q = (reference_value - raw_value) / denom
    return _clamp(float(q), 0.0, 1.0)


def nonlinear_points(q: float, p: float) -> float:
    quality = _clamp(float(q), 0.0, 1.0)
    curve = max(float(p), 1.0)
    return 100.0 * (1.0 - math.pow(1.0 - quality, curve))


def linear_points(q: float) -> float:
    return 100.0 * _clamp(float(q), 0.0, 1.0)


def infer_curve_p(
    raw_metrics: Iterable[float],
    *,
    ideal: float,
    reference: float,
    direction: str,
    default_p: float,
) -> float:
    qualities = []
    for raw in raw_metrics:
        try:
            q = normalize_quality(float(raw), ideal=ideal, reference=reference, direction=direction)
        except Exception:
            continue
        if 0.0 < q < 1.0:
            qualities.append(q)

    if len(qualities) < 3:
        return max(default_p, 1.0)

    qualities.sort()
    idx = int(round(0.75 * (len(qualities) - 1)))
    q75 = qualities[idx]
    if q75 <= 0.0 or q75 >= 1.0:
        return max(default_p, 1.0)

    target_score = 70.0
    numerator = math.log(max(1e-9, 1.0 - target_score / 100.0))
    denominator = math.log(max(1e-9, 1.0 - q75))
    if abs(denominator) < 1e-12:
        return max(default_p, 1.0)

    inferred = numerator / denominator
    if not math.isfinite(inferred):
        return max(default_p, 1.0)
    return _clamp(float(inferred), 1.2, 6.0)


def extract_raw_metric(metrics, metric_name: str | None = None) -> Optional[float]:
    if metrics is None:
        return None

    if isinstance(metrics, dict):
        raw_value = _to_float(metrics.get("raw_metric"))
        if raw_value is not None:
            return raw_value

        preferred = (metric_name or "").strip()
        if preferred:
            preferred_value = _to_float(metrics.get(preferred))
            if preferred_value is not None:
                return preferred_value

        # When score_100 is already present, "metric"/"score" are likely final points.
        has_final_score = _to_float(metrics.get("score_100")) is not None or _to_float(metrics.get("metric_score")) is not None

        if not has_final_score:
            for key in ("metric", "score", "accuracy", "f1", "auc", "rmse", "mse", "mae", "r2"):
                value = _to_float(metrics.get(key))
                if value is not None:
                    return value

        for value in metrics.values():
            number = _to_float(value)
            if number is not None:
                return number
        return None

    return _to_float(metrics)


def extract_score_100(metrics) -> Optional[float]:
    if isinstance(metrics, dict):
        for key in ("score_100", "metric_score"):
            value = _to_float(metrics.get(key))
            if value is not None:
                return _clamp(value, 0.0, 100.0)
    return None


def score_from_raw(
    raw_metric: float,
    *,
    metric_name: str,
    direction: str,
    ideal: float,
    reference: float | None,
    curve_p: float | None,
) -> tuple[float, str]:
    if reference is None:
        linear_ref = default_linear_reference(metric_name, direction, ideal)
        q = normalize_quality(raw_metric, ideal=ideal, reference=linear_ref, direction=direction)
        return linear_points(q), "linear"

    q = normalize_quality(raw_metric, ideal=ideal, reference=reference, direction=direction)
    p = max(curve_p or 1.0, 1.0)
    return nonlinear_points(q, p), "nonlinear"
