from __future__ import annotations

import builtins
import os
import re
import shutil
import atexit
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
import venv
from urllib.parse import urlparse
from urllib.request import urlopen

from django.conf import settings
from django.utils import timezone

from .vm_agent import dispose_vm_agent, get_vm_agent
from .vm_exceptions import VmError
from .vm_manager import get_vm_manager
from .vm_models import VirtualMachine


class SessionNotFoundError(Exception):
    """Raised when runtime operations reference a missing session."""

DEFAULT_SESSION_TTL_SECONDS = 3600
DEFAULT_RUNTIME_ROOT = Path(
    getattr(settings, "RUNTIME_SANDBOX_ROOT", Path(settings.BASE_DIR) / "notebook_sessions")
)
DEFAULT_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass
class RuntimeSession:
    namespace: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    workdir: Path
    python_exec: Path | None = None
    vm: VirtualMachine | None = None


@dataclass
class RuntimeExecutionResult:
    stdout: str
    stderr: str
    error: str | None
    variables: Dict[str, str]


_sessions: Dict[str, RuntimeSession] = {}
_shutdown_hooks_registered = False


def _resolve_now(value: datetime | None = None) -> datetime:
    resolved = value or timezone.now()
    if timezone.is_naive(resolved):
        resolved = timezone.make_aware(resolved, timezone.get_current_timezone())
    return resolved


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
    existing = _sessions.get(session_id)
    if existing is not None:
        existing.updated_at = current
        return existing

    vm = _ensure_session_vm(session_id, now=current)
    workdir = vm.workspace_path
    workdir.mkdir(parents=True, exist_ok=True)
    if vm.backend == "local":
        namespace = _new_namespace()
        python_exec: Path | None = None
        venv_path = workdir / ".venv"
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
    else:
        namespace = {}
        python_exec = None

    session = RuntimeSession(
        namespace=namespace,
        created_at=current,
        updated_at=current,
        workdir=workdir,
        python_exec=python_exec,
        vm=vm,
    )
    if vm.backend == "local":
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
    removed = stop_session(session_id)
    if not removed:
        raise SessionNotFoundError(f"Session '{session_id}' not found")
    return create_session(session_id, now=now)


def stop_session(session_id: str) -> bool:
    session = _sessions.pop(session_id, None)
    dispose_vm_agent(session_id)
    _destroy_session_vm(session_id)
    removed = False
    if session:
        removed = True
        if session.workdir.exists():
            _clear_directory(session.workdir)
    return removed


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
            stop_session(session_id)
    return expired


def cleanup_all_sessions() -> None:
    """Terminate all known sessions and purge leftover directories."""
    for session_id in list(_sessions.keys()):
        stop_session(session_id)
    _purge_runtime_root()


def _purge_runtime_root() -> None:
    for root in _iter_runtime_roots():
        for path in root.glob("runner-*"):
            _clear_directory(path)


def _iter_runtime_roots() -> List[Path]:
    roots: List[Path] = []
    sandbox_root = getattr(settings, "RUNTIME_SANDBOX_ROOT", None)
    vm_root = getattr(settings, "RUNTIME_VM_ROOT", None)
    candidates = [
        sandbox_root or DEFAULT_RUNTIME_ROOT,
        vm_root or DEFAULT_RUNTIME_ROOT,
    ]
    seen: set[Path] = set()
    resolved: List[Path] = []
    for candidate in candidates:
        if candidate is None:
            continue
        path = Path(candidate).resolve()
        if path in seen:
            continue
        path.mkdir(parents=True, exist_ok=True)
        seen.add(path)
        resolved.append(path)
    return resolved


def register_runtime_shutdown_hooks() -> None:
    global _shutdown_hooks_registered
    if _shutdown_hooks_registered:
        return
    atexit.register(cleanup_all_sessions)
    _shutdown_hooks_registered = True


register_runtime_shutdown_hooks()


def _require_session(session_id: str) -> RuntimeSession:
    session = get_session(session_id, touch=False)
    if session is None:
        raise SessionNotFoundError(f"Session '{session_id}' not found")
    return session


def _ensure_session_vm(session_id: str, *, now: datetime | None = None) -> VirtualMachine:
    manager = get_vm_manager()
    return manager.ensure_session_vm(session_id, now=now)


def _destroy_session_vm(session_id: str) -> None:
    try:
        manager = get_vm_manager()
    except Exception:
        return
    try:
        manager.destroy_session_vm(session_id)
    except VmError:
        return


def run_code(session_id: str, code: str) -> RuntimeExecutionResult:
    session = _require_session(session_id)
    agent = get_vm_agent(session_id, session)
    result_payload = agent.exec_code(code)
    session.updated_at = _resolve_now()

    return RuntimeExecutionResult(
        stdout=result_payload.get("stdout", ""),
        stderr=result_payload.get("stderr", ""),
        error=result_payload.get("error"),
        variables=result_payload.get("variables", {}),
    )


__all__ = [
    "RuntimeSession",
    "RuntimeExecutionResult",
    "DEFAULT_SESSION_TTL_SECONDS",
    "create_session",
    "get_session",
    "reset_session",
    "stop_session",
    "cleanup_expired",
    "cleanup_all_sessions",
    "run_code",
    "SessionNotFoundError",
    "register_runtime_shutdown_hooks",
]
