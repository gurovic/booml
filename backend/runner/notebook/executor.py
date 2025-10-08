from __future__ import annotations

import os
import sys
import time
import uuid
import signal
import csv
import subprocess
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

try:
    import resource
except Exception:
    resource = None  # type: ignore

from .config import cfg


@dataclass
class RunStats:
    exit_code: int
    elapsed_ms: int
    cpu_s: float | None
    mem_mb: int | None
    timeout: bool


@dataclass
class OutputItem:
    type: str
    data: Dict[str, Any]


@dataclass
class RunResult:
    ok: bool
    run_id: str
    outputs: List[OutputItem]
    stderr: str
    stats: RunStats
    errors: List[Dict[str, Any]]


def _apply_limits() -> None:
    os.setsid()
    if resource is None:
        return
    resource.setrlimit(resource.RLIMIT_CPU, (cfg.TIMEOUT_S + 1, cfg.TIMEOUT_S + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (cfg.MAX_FILE_BYTES, cfg.MAX_FILE_BYTES))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))


def build_env() -> Dict[str, str]:
    return dict(cfg.PYTHON_ENV)


def collect_outputs(run_dir: Path, stdout_bytes: bytes) -> List[OutputItem]:
    outputs: List[OutputItem] = []

    stdout_text = (stdout_bytes or b"")[:cfg.MAX_STD_BYTES].decode("utf-8", errors="replace")
    if stdout_text.strip():
        outputs.append(OutputItem("text", {"text": stdout_text}))

    for path in sorted(run_dir.glob("*.htm*")):
        try:
            if path.stat().st_size <= cfg.MAX_FILE_BYTES:
                outputs.append(OutputItem("html", {
                    "name": path.name,
                    "html": path.read_text(encoding="utf-8", errors="replace")
                }))
        except Exception:
            continue

    for path in sorted(run_dir.iterdir()):
        try:
            if path.suffix.lower() in cfg.IMG_EXTENSIONS and path.stat().st_size <= cfg.MAX_FILE_BYTES:
                outputs.append(OutputItem("image", {"name": path.name}))
        except Exception:
            continue

    for path in sorted(run_dir.glob("*.csv")):
        try:
            if path.stat().st_size <= cfg.MAX_FILE_BYTES:
                rows: List[List[str]] = []
                with path.open(newline="", encoding="utf-8", errors="replace") as f:
                    reader = csv.reader(f)
                    for i, row in enumerate(reader):
                        if i >= cfg.CSV_PREVIEW_ROWS:
                            break
                        rows.append(row)
                columns = rows[0] if rows else []
                body = rows[1:] if rows else []
                outputs.append(OutputItem("table", {
                    "name": path.name,
                    "columns": columns,
                    "rows": body,
                    "truncated": len(rows) >= cfg.CSV_PREVIEW_ROWS
                }))
        except Exception:
            continue

    return outputs


def run_python(code: str, media_root: Path, run_id: str | None = None, timeout_s: int = cfg.TIMEOUT_S) -> RunResult:
    started_at = time.time()
    rid = run_id or uuid.uuid4().hex
    run_dir = media_root / cfg.RUNS_SUBDIR / rid

    try:
        code_bytes = code.encode("utf-8", errors="replace")
        if len(code_bytes) > cfg.MAX_CODE_BYTES:
            return RunResult(
                ok=False,
                run_id=rid,
                outputs=[],
                stderr="",
                stats=RunStats(-1, 0, None, None, False),
                errors=[{"code": "payload_too_large", "msg": f"code > {cfg.MAX_CODE_BYTES} bytes"}],
            )

        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "main.py").write_bytes(code_bytes)

        cmd = [sys.executable, *cfg.PYTHON_FLAGS, "main.py"]

        proc = subprocess.Popen(
            cmd,
            cwd=str(run_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=build_env(),
            preexec_fn=_apply_limits if os.name == "posix" else None,
        )

        timed_out = False
        try:
            stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                if os.name == "posix":
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
            finally:
                stdout_bytes, stderr_bytes = proc.communicate()

        elapsed_ms = int((time.time() - started_at) * 1000)

        cpu_s = mem_mb = None
        if resource is not None:
            try:
                rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
                cpu_s = float(rusage.ru_utime + rusage.ru_stime)
                rss_kb = int(rusage.ru_maxrss if sys.platform != "darwin" else rusage.ru_maxrss / 1024)
                mem_mb = rss_kb // 1024
            except Exception:
                cpu_s = mem_mb = None

        outputs = collect_outputs(run_dir, stdout_bytes or b"")
        stderr_text = (stderr_bytes or b"")[:cfg.MAX_STD_BYTES].decode("utf-8", errors="replace")

        ok = (proc.returncode == 0) and (not timed_out)
        errors: List[Dict[str, Any]] = []
        if timed_out:
            errors.append({"code": "timeout", "msg": f"execution exceeded {timeout_s}s"})
        if proc.returncode != 0 and not timed_out:
            errors.append({"code": "nonzero_exit", "msg": f"exit {proc.returncode}"})

        return RunResult(
            ok=ok,
            run_id=rid,
            outputs=outputs,
            stderr=stderr_text,
            stats=RunStats(int(proc.returncode or 0), elapsed_ms, cpu_s, mem_mb, timed_out),
            errors=errors,
        )

    except Exception as e:
        return RunResult(
            ok=False,
            run_id=rid,
            outputs=[],
            stderr="",
            stats=RunStats(-1, int((time.time() - started_at) * 1000), None, None, False),
            errors=[{"code": "internal", "msg": str(e), "traceback": traceback.format_exc(limit=5)}],
        )
