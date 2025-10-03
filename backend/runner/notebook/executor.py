from __future__ import annotations
import os, sys, time, uuid, signal, csv, subprocess, traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

try:
    import resource  # POSIX-only
except Exception:
    resource = None

RUNS_SUBDIR = "runs"
TIMEOUT_S = 10
MAX_CODE_BYTES = 200_000
MAX_STD_BYTES = 500_000
MAX_FILE_BYTES = 10 * 1024 * 1024
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg"}


@dataclass
class RunStats:
    exit_code: int
    elapsed_ms: int
    cpu_s: float | None
    mem_mb: int | None
    timeout: bool


@dataclass
class OutputItem:
    type: str  # "text" | "html" | "image" | "table" | "error"
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
    resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT_S + 1, TIMEOUT_S + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE_BYTES, MAX_FILE_BYTES))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))


def _env() -> Dict[str, str]:
    return {
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
    }


def _collect(root: Path, stdout_b: bytes) -> List[OutputItem]:
    outs: List[OutputItem] = []

    txt = (stdout_b or b"")[:MAX_STD_BYTES].decode("utf-8", errors="replace")
    if txt.strip():
        outs.append(OutputItem("text", {"text": txt}))

    for fp in sorted(root.glob("*.htm*")):
        if fp.stat().st_size <= MAX_FILE_BYTES:
            outs.append(OutputItem("html", {"name": fp.name, "html": fp.read_text("utf-8", errors="replace")}))

    for fp in sorted(root.iterdir()):
        if fp.suffix.lower() in IMG_EXT and fp.stat().st_size <= MAX_FILE_BYTES:
            outs.append(OutputItem("image", {"name": fp.name}))

    for fp in sorted(root.glob("*.csv")):
        if fp.stat().st_size <= MAX_FILE_BYTES:
            rows: List[List[str]] = []
            with fp.open(newline="", encoding="utf-8", errors="replace") as f:
                rdr = csv.reader(f)
                for i, row in enumerate(rdr):
                    if i >= 1000: break
                    rows.append(row)
            cols = rows[0] if rows else []
            body = rows[1:] if rows else []
            outs.append(
                OutputItem("table", {"name": fp.name, "columns": cols, "rows": body, "truncated": len(rows) >= 1000}))
    return outs


def run_python(code: str, media_root: Path, run_id: str | None = None, timeout_s: int = TIMEOUT_S) -> RunResult:
    """Запуск Python с таймаутом и сбором артефактов в media/runs/<run_id>/."""
    t0 = time.time()
    rid = run_id or uuid.uuid4().hex
    root = media_root / RUNS_SUBDIR / rid
    try:
        b = code.encode("utf-8", errors="replace")
        if len(b) > MAX_CODE_BYTES:
            return RunResult(False, rid, [], "", RunStats(-1, 0, None, None, False),
                             [{"code": "payload_too_large", "msg": f"code > {MAX_CODE_BYTES} bytes"}])

        root.mkdir(parents=True, exist_ok=True)
        (root / "main.py").write_bytes(b)

        cmd = [sys.executable, "-I", "-S", "-B", "main.py"]
        proc = subprocess.Popen(cmd, cwd=str(root),
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=_env(),
                                preexec_fn=_apply_limits if os.name == "posix" else None)
        timeout = False
        try:
            out_b, err_b = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timeout = True
            try:
                if os.name == "posix":
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
            finally:
                out_b, err_b = proc.communicate()

        elapsed_ms = int((time.time() - t0) * 1000)
        cpu_s = mem_mb = None
        if resource is not None:
            ru = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu_s = float(ru.ru_utime + ru.ru_stime)
            rss_kb = int(ru.ru_maxrss if sys.platform != "darwin" else ru.ru_maxrss / 1024)
            mem_mb = rss_kb // 1024

        outs = _collect(root, out_b or b"")
        stderr = (err_b or b"")[:MAX_STD_BYTES].decode("utf-8", errors="replace")
        ok = (proc.returncode == 0) and (not timeout)
        errs: List[Dict[str, Any]] = []
        if timeout: errs.append({"code": "timeout", "msg": f"execution exceeded {timeout_s}s"})
        if proc.returncode != 0 and not timeout: errs.append({"code": "nonzero_exit", "msg": f"exit {proc.returncode}"})

        return RunResult(ok, rid, outs, stderr, RunStats(int(proc.returncode or 0), elapsed_ms, cpu_s, mem_mb, timeout),
                         errs)
    except Exception as e:
        return RunResult(False, rid, [], "", RunStats(-1, int((time.time() - t0) * 1000), None, None, False),
                         [{"code": "internal", "msg": str(e), "traceback": traceback.format_exc(limit=5)}])
