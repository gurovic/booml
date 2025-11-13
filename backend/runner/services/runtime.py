from __future__ import annotations

import builtins
import io
import os
import re
import shutil
import traceback
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
import venv
from urllib.parse import urlparse
from urllib.request import urlopen

from django.conf import settings
from django.utils import timezone

DEFAULT_SESSION_TTL_SECONDS = 3600
DEFAULT_RUNTIME_ROOT = Path(
    getattr(settings, "RUNTIME_SANDBOX_ROOT", Path(settings.BASE_DIR) / "runtime_sessions")
)
DEFAULT_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass
class RuntimeSession:
    namespace: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    workdir: Path
    python_exec: Path | None = None


@dataclass
class RuntimeExecutionResult:
    stdout: str
    stderr: str
    error: str | None
    variables: Dict[str, str]


_sessions: Dict[str, RuntimeSession] = {}


def _resolve_now(value: datetime | None = None) -> datetime:
    resolved = value or timezone.now()
    if timezone.is_naive(resolved):
        resolved = timezone.make_aware(resolved, timezone.get_current_timezone())
    return resolved


def _sanitize_session_id(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)


def _ensure_session_dir(session_id: str) -> Path:
    safe_name = _sanitize_session_id(session_id)
    session_dir = DEFAULT_RUNTIME_ROOT / safe_name
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _clear_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def _new_namespace() -> Dict[str, Any]:
    sandbox_builtins: Dict[str, Any] = {}
    for name in dir(builtins):
        sandbox_builtins[name] = getattr(builtins, name)
    return {"__builtins__": sandbox_builtins}


def _build_download_helper(session: RuntimeSession):
    def download_file(url: str, *, filename: str | None = None, chunk_size: int = 1024 * 1024) -> str:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("URL must be a non-empty string")
        parsed = urlparse(url)
        basename = Path(parsed.path or "").name
        target_name = filename or basename or "downloaded.file"
        target_path = session.workdir / target_name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        size = int(chunk_size or 0)
        if size <= 0:
            size = 1024 * 1024
        with urlopen(url) as response, target_path.open("wb") as destination:
            while True:
                data = response.read(size)
                if not data:
                    break
                destination.write(data)
        return str(target_path.relative_to(session.workdir))

    download_file.__name__ = "download_file"
    return download_file


@contextmanager
def _session_cwd(path: Path):
    original = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def create_session(session_id: str, *, now: datetime | None = None) -> RuntimeSession:
    current = _resolve_now(now)
    workdir = _ensure_session_dir(session_id)
    namespace = _new_namespace()
    venv_path = workdir / ".venv"
    python_exec: Path | None = None
    try:
        if not venv_path.exists():
            builder = venv.EnvBuilder(with_pip=False, symlinks=os.name != "nt")
            builder.create(venv_path)
        if os.name == "nt":
            candidate = venv_path / "Scripts" / "python.exe"
        else:
            candidate = venv_path / "bin" / "python"
        if candidate.exists():
            python_exec = candidate
    except Exception:
        python_exec = None

    session = RuntimeSession(
        namespace=namespace,
        created_at=current,
        updated_at=current,
        workdir=workdir,
        python_exec=python_exec,
    )
    session.namespace["download_file"] = _build_download_helper(session)
    session.namespace.setdefault("__name__", "__main__")
    _sessions[session_id] = session
    return session


def get_session(session_id: str, *, touch: bool = True, now: datetime | None = None) -> RuntimeSession | None:
    session = _sessions.get(session_id)
    if session and touch:
        session.updated_at = _resolve_now(now)
    return session


def reset_session(session_id: str, *, now: datetime | None = None) -> RuntimeSession:
    old = _sessions.pop(session_id, None)
    if old:
        _clear_directory(old.workdir)
    return create_session(session_id, now=now)


def cleanup_expired(
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    *,
    now: datetime | None = None,
) -> List[str]:
    if ttl_seconds <= 0:
        ttl_seconds = 0
    current = _resolve_now(now)
    cutoff = current - timedelta(seconds=ttl_seconds)
    expired: List[str] = []
    for session_id, session in list(_sessions.items()):
        if session.updated_at < cutoff:
            expired.append(session_id)
            _sessions.pop(session_id, None)
            _clear_directory(session.workdir)
    return expired


def _get_or_create_session(session_id: str) -> RuntimeSession:
    session = get_session(session_id, touch=False)
    if session is None:
        session = create_session(session_id)
    return session


def _snapshot_variables(namespace: Dict[str, Any]) -> Dict[str, str]:
    snapshot: Dict[str, str] = {}
    for key, value in namespace.items():
        if key == "__builtins__":
            continue
        if key.startswith("__") and key.endswith("__"):
            continue
        try:
            snapshot[key] = repr(value)
        except Exception:
            snapshot[key] = f"<unrepresentable {type(value).__name__}>"
    return snapshot


def run_code(session_id: str, code: str) -> RuntimeExecutionResult:
    session = _get_or_create_session(session_id)
    namespace = session.namespace

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    error: str | None = None

    with _session_cwd(session.workdir), redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        try:
            exec(code, namespace, namespace)
        except Exception:
            error = traceback.format_exc()

    session.updated_at = _resolve_now()

    return RuntimeExecutionResult(
        stdout=stdout_buffer.getvalue(),
        stderr=stderr_buffer.getvalue(),
        error=error,
        variables=_snapshot_variables(namespace),
    )


__all__ = [
    "RuntimeSession",
    "RuntimeExecutionResult",
    "DEFAULT_SESSION_TTL_SECONDS",
    "create_session",
    "get_session",
    "reset_session",
    "cleanup_expired",
    "run_code",
]
