from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, Dict
import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default


@dataclass(frozen=True)
class RunnerConfig:
    RUNS_SUBDIR: str = os.getenv("RUNS_SUBDIR", "runs")

    TIMEOUT_S: int = _int("RUN_TIMEOUT_S", 10)
    MAX_CODE_BYTES: int = _int("RUN_MAX_CODE_BYTES", 200_000)
    MAX_STD_BYTES: int = _int("RUN_MAX_STD_BYTES", 500_000)
    MAX_FILE_BYTES: int = _int("RUN_MAX_FILE_BYTES", 10 * 1024 * 1024)
    CSV_PREVIEW_ROWS: int = _int("RUN_CSV_PREVIEW_ROWS", 1000)

    IMG_EXTENSIONS: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".gif", ".svg")
    PYTHON_FLAGS: Tuple[str, ...] = ("-I", "-S", "-B")
    PYTHON_ENV: Dict[str, str] = field(default_factory=lambda: {
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
    })


cfg = RunnerConfig()
