from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

@dataclass
class SubmissionModel:
    """
    Лёгкая модель-обёртка для результата проверки.
    Это НЕ django.db.models.Model — миграций не требует.
    """
    problem_code: Optional[str]
    user_display: Optional[str]
    status: Optional[str]
    time_ms: Optional[int]
    memory_kb: Optional[int]
    metrics: List[Dict[str, Any]]
    errors: List[Any]
    logs: Optional[str]
    raw: Dict[str, Any]
    created_at: str

    @classmethod
    def from_raw(cls, raw: Dict[str, Any], problem_code: Optional[str] = None, user_display: Optional[str] = None):
        if not isinstance(raw, dict):
            raw = {}
        # поддерживаем обёртки типа {"result": {...}}
        for key in ("result", "submission", "submission_result", "data"):
            if key in raw and isinstance(raw[key], dict):
                raw = raw[key]
                break

        status = (raw.get("status") or "").lower()
        time_ms = raw.get("time")
        memory_kb = raw.get("memory")
        metrics = raw.get("metrics") or []
        errors = raw.get("errors") or []
        logs = raw.get("logs") or raw.get("log") or ""
        created_at = raw.get("created_at") or datetime.utcnow().isoformat() + "Z"

        # Нормализация metrics -> list of {"name":..., "value":...}
        norm_metrics = []
        if isinstance(metrics, dict):
            norm_metrics = [{"name": k, "value": v} for k, v in metrics.items()]
        elif isinstance(metrics, list):
            for item in metrics:
                if isinstance(item, dict) and ("name" in item or "value" in item):
                    norm_metrics.append(item)
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    norm_metrics.append({"name": item[0], "value": item[1]})
                else:
                    norm_metrics.append({"name": str(item), "value": ""})
        else:
            norm_metrics = [{"name": "metrics", "value": str(metrics)}]

        return cls(
            problem_code = problem_code or raw.get("problem_code"),
            user_display = user_display or raw.get("user_display"),
            status = status,
            time_ms = time_ms,
            memory_kb = memory_kb,
            metrics = norm_metrics,
            errors = errors if isinstance(errors, list) else [errors] if errors else [],
            logs = logs,
            raw = raw,
            created_at = created_at,
        )

    def to_json(self) -> str:
        return json.dumps({
            "problem_code": self.problem_code,
            "user_display": self.user_display,
            "status": self.status,
            "time_ms": self.time_ms,
            "memory_kb": self.memory_kb,
            "metrics": self.metrics,
            "errors": self.errors,
            "logs": self.logs,
            "created_at": self.created_at,
            "raw": self.raw,
        }, ensure_ascii=False, indent=2)
