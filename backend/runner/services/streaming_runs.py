from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple
import threading
import time
import uuid

from .runtime import RuntimeExecutionResult, SessionNotFoundError, get_session, run_code_stream


MAX_STREAM_CHUNK_BYTES = 64 * 1024
RUN_TTL_SECONDS = 3600


@dataclass
class StreamingRun:
    run_id: str
    session_id: str
    cell_id: int
    notebook_id: int
    stdout_path: Path
    stderr_path: Path
    status: str = "running"
    started_at: float = 0.0
    finished_at: float | None = None
    error: str | None = None
    result: RuntimeExecutionResult | None = None


_RUNS: Dict[str, StreamingRun] = {}
_LOCK = threading.Lock()


def start_streaming_run(*, session_id: str, cell_id: int, notebook_id: int, code: str) -> StreamingRun:
    _cleanup_expired_runs()
    session = get_session(session_id, touch=False)
    if session is None:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    run_id = uuid.uuid4().hex
    stream_dir = session.workdir / ".streams"
    stream_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = stream_dir / f"{run_id}.stdout"
    stderr_path = stream_dir / f"{run_id}.stderr"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")

    run = StreamingRun(
        run_id=run_id,
        session_id=session_id,
        cell_id=cell_id,
        notebook_id=notebook_id,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        status="running",
        started_at=time.time(),
    )
    with _LOCK:
        _RUNS[run_id] = run

    thread = threading.Thread(target=_execute_run, args=(run, code), daemon=True)
    thread.start()
    return run


def get_streaming_run(run_id: str) -> StreamingRun | None:
    _cleanup_expired_runs()
    with _LOCK:
        return _RUNS.get(run_id)


def read_stream_output(run: StreamingRun, *, stdout_offset: int, stderr_offset: int) -> Tuple[str, str, int, int]:
    stdout_chunk, stdout_next = _read_chunk(run.stdout_path, stdout_offset)
    stderr_chunk, stderr_next = _read_chunk(run.stderr_path, stderr_offset)
    return stdout_chunk, stderr_chunk, stdout_next, stderr_next


def _execute_run(run: StreamingRun, code: str) -> None:
    try:
        result = run_code_stream(
            run.session_id,
            code,
            stdout_path=run.stdout_path,
            stderr_path=run.stderr_path,
        )
        run.result = result
        run.status = "finished"
    except SessionNotFoundError as exc:
        run.status = "error"
        run.error = str(exc)
    except Exception as exc:  # pragma: no cover - defensive
        run.status = "error"
        run.error = str(exc)
    finally:
        run.finished_at = time.time()


def _read_chunk(path: Path, offset: int) -> Tuple[str, int]:
    if offset < 0:
        offset = 0
    if not path.exists():
        return "", offset
    try:
        with path.open("rb") as fh:
            fh.seek(offset)
            chunk = fh.read(MAX_STREAM_CHUNK_BYTES)
            if not chunk:
                return "", offset
            return chunk.decode("utf-8", errors="replace"), offset + len(chunk)
    except Exception:
        return "", offset


def _cleanup_expired_runs() -> None:
    now = time.time()
    expired: list[str] = []
    with _LOCK:
        for run_id, run in list(_RUNS.items()):
            if run.finished_at is None:
                continue
            if now - run.finished_at > RUN_TTL_SECONDS:
                expired.append(run_id)
        for run_id in expired:
            run = _RUNS.pop(run_id, None)
            if run:
                for path in (run.stdout_path, run.stderr_path):
                    try:
                        path.unlink(missing_ok=True)
                    except Exception:
                        pass
