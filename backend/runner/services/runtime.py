from __future__ import annotations

import atexit
import builtins
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import venv
from urllib.parse import urlparse
from urllib.request import urlopen

from django.conf import settings
from django.utils import timezone

from .vm_agent import _handle_shell_commands, dispose_vm_agent, get_vm_agent
from .vm_exceptions import VmError
from .vm_manager import get_vm_manager
from .vm_models import VirtualMachine

logger = logging.getLogger(__name__)


class SessionNotFoundError(Exception):
    """Raised when runtime operations reference a missing session."""


DEFAULT_SESSION_TTL_SECONDS = 3600
DEFAULT_RUNTIME_ROOT = Path(
    getattr(settings, "RUNTIME_SANDBOX_ROOT", Path(settings.BASE_DIR) / "media" / "notebook_sessions")
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
    outputs: List[Dict[str, object]]
    artifacts: List[Dict[str, object]]




_sessions: Dict[str, RuntimeSession] = {}
_shutdown_hooks_registered = False
_backend: "ExecutionBackend | None" = None


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
    def download_file(
        url: str,
        *,
        filename: str | None = None,
        chunk_size: int = 1024 * 1024,
        timeout: float = 30.0,
    ) -> str:
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
        with urlopen(url, timeout=timeout) as response, target_path.open("wb") as destination:
            while True:
                data = response.read(size)
                if not data:
                    break
                destination.write(data)
        return str(target_path.relative_to(session.workdir))

    download_file.__name__ = "download_file"
    return download_file


def _prepare_local_python_exec(workdir: Path) -> Path | None:
    venv_path = workdir / ".venv"
    try:
        if not venv_path.exists():
            builder = venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt")
            builder.create(venv_path)
        if os.name == "nt":
            candidate = venv_path / "Scripts" / "python.exe"
        else:
            candidate = venv_path / "bin" / "python"
        if candidate.exists():
            return candidate
    except Exception:
        return None
    return None


def _write_stream_files(stdout_path: Path, stderr_path: Path, stdout: str, stderr: str) -> None:
    if stdout_path:
        try:
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            stdout_path.write_text(stdout or "", encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to write stdout stream to %s: %s", stdout_path, exc)
    if stderr_path:
        try:
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            stderr_path.write_text(stderr or "", encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to write stderr stream to %s: %s", stderr_path, exc)


def _ensure_session_vm(
    session_id: str,
    *,
    now: datetime | None = None,
    overrides: Dict[str, object] | None = None,
) -> VirtualMachine:
    manager = get_vm_manager()
    return manager.ensure_session_vm(session_id, now=now, overrides=overrides)


def _destroy_session_vm(session_id: str) -> None:
    try:
        manager = get_vm_manager()
    except Exception:
        return
    try:
        manager.destroy_session_vm(session_id)
    except VmError:
        return


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


def _purge_runtime_root() -> None:
    for root in _iter_runtime_roots():
        for path in root.glob("runner-*"):
            _clear_directory(path)


def _get_session_ttl_seconds() -> int:
    value = getattr(settings, "RUNTIME_SESSION_TTL_SECONDS", DEFAULT_SESSION_TTL_SECONDS)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return DEFAULT_SESSION_TTL_SECONDS


class ExecutionBackend:
    """Pluggable execution backend contract."""

    def __init__(self, *, sessions: Dict[str, RuntimeSession]):
        self.sessions = sessions

    def create_session(
        self,
        session_id: str,
        *,
        now: datetime | None = None,
        overrides: Dict[str, object] | None = None,
    ) -> RuntimeSession:  # pragma: no cover - abstract
        raise NotImplementedError

    def run_code(self, session_id: str, code: str) -> RuntimeExecutionResult:  # pragma: no cover - abstract
        raise NotImplementedError

    def run_code_stream(
        self,
        session_id: str,
        code: str,
        *,
        stdout_path: Path,
        stderr_path: Path,
    ) -> RuntimeExecutionResult:
        result = self.run_code(session_id, code)
        _write_stream_files(stdout_path, stderr_path, result.stdout, result.stderr)
        return result

    def stop_session(self, session_id: str) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError

    def get_session(self, session_id: str, *, touch: bool = True, now: datetime | None = None) -> RuntimeSession | None:
        current = _resolve_now(now)
        self._auto_cleanup_expired(now=current)
        session = self.sessions.get(session_id)
        if session and touch:
            session.updated_at = current
        return session

    def reset_session(
        self,
        session_id: str,
        *,
        now: datetime | None = None,
        overrides: Dict[str, object] | None = None,
    ) -> RuntimeSession:
        removed = self.stop_session(session_id)
        if not removed:
            raise SessionNotFoundError(f"Session '{session_id}' not found")
        return self.create_session(session_id, now=now, overrides=overrides)

    def cleanup_expired(
        self,
        ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        *,
        now: datetime | None = None,
    ) -> List[str]:
        if ttl_seconds <= 0:
            ttl_seconds = 0
        current = _resolve_now(now)
        cutoff = current - timedelta(seconds=ttl_seconds)
        expired: List[str] = []
        for session_id, session in list(self.sessions.items()):
            if session.updated_at < cutoff:
                expired.append(session_id)
                self.stop_session(session_id)
        return expired

    def cleanup_all_sessions(self) -> None:
        for session_id in list(self.sessions.keys()):
            self.stop_session(session_id)
        _purge_runtime_root()

    def _auto_cleanup_expired(self, *, now: datetime | None = None) -> None:
        ttl = _get_session_ttl_seconds()
        self.cleanup_expired(ttl_seconds=ttl, now=now)

    def _require_session(self, session_id: str, *, now: datetime | None = None) -> RuntimeSession:
        session = self.get_session(session_id, touch=False, now=now)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found")
        return session


class LegacyExecutionBackend(ExecutionBackend):
    """Legacy in-process executor that preserves existing behavior."""

    def create_session(
        self,
        session_id: str,
        *,
        now: datetime | None = None,
        overrides: Dict[str, object] | None = None,
    ) -> RuntimeSession:
        current = _resolve_now(now)
        self._auto_cleanup_expired(now=current)
        existing = self.sessions.get(session_id)
        if existing is not None:
            existing.updated_at = current
            return existing

        vm = _ensure_session_vm(session_id, now=current, overrides=overrides)
        workdir = vm.workspace_path
        workdir.mkdir(parents=True, exist_ok=True)
        namespace = {}
        python_exec: Path | None = None

        if vm.backend == "local":
            namespace = _new_namespace()
            python_exec = _prepare_local_python_exec(workdir)

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
        self.sessions[session_id] = session
        return session

    def stop_session(self, session_id: str) -> bool:
        session = self.sessions.pop(session_id, None)
        dispose_vm_agent(session_id)
        _destroy_session_vm(session_id)
        removed = False
        if session:
            removed = True
            if session.workdir.exists():
                _clear_directory(session.workdir)
        return removed

    def run_code(self, session_id: str, code: str) -> RuntimeExecutionResult:
        session = self._require_session(session_id)
        agent = get_vm_agent(session_id, session)
        result_payload = agent.exec_code(code)
        session.updated_at = _resolve_now()

        return RuntimeExecutionResult(
            stdout=result_payload.get("stdout", ""),
            stderr=result_payload.get("stderr", ""),
            error=result_payload.get("error"),
            variables=result_payload.get("variables", {}),
            outputs=result_payload.get("outputs", []),
            artifacts=result_payload.get("artifacts", []),
        )

    def run_code_stream(
        self,
        session_id: str,
        code: str,
        *,
        stdout_path: Path,
        stderr_path: Path,
    ) -> RuntimeExecutionResult:
        session = self._require_session(session_id)
        agent = get_vm_agent(session_id, session)
        result_payload = agent.exec_code_stream(code, stdout_path=stdout_path, stderr_path=stderr_path)
        session.updated_at = _resolve_now()

        return RuntimeExecutionResult(
            stdout=result_payload.get("stdout", ""),
            stderr=result_payload.get("stderr", ""),
            error=result_payload.get("error"),
            variables=result_payload.get("variables", {}),
            outputs=result_payload.get("outputs", []),
            artifacts=result_payload.get("artifacts", []),
        )




def _build_backend() -> ExecutionBackend:
    backend_name = (
        str(getattr(settings, "RUNTIME_EXECUTION_BACKEND", os.environ.get("RUNTIME_EXECUTION_BACKEND", "legacy")) or "legacy")
        .strip()
        .lower()
    )
    # Treat empty/default/legacy strings as legacy for backward compatibility.
    if backend_name in ("", "legacy", "default"):
        return LegacyExecutionBackend(sessions=_sessions)
    # Backward compatibility: the old Jupyter backend has been removed, but
    # existing deployments may still use RUNTIME_EXECUTION_BACKEND="jupyter".
    # Fall back to the legacy backend and emit a warning instead of crashing.
    if backend_name == "jupyter":
        logger.warning(
            "Execution backend 'jupyter' has been removed; falling back to 'legacy'. "
            "Please update RUNTIME_EXECUTION_BACKEND (or corresponding Django setting) "
            "to 'legacy'."
        )
        return LegacyExecutionBackend(sessions=_sessions)
    raise ValueError(
        "Unsupported execution backend: %r. Supported backends: 'legacy'. "
        "Note: the 'jupyter' backend has been removed; use 'legacy' or "
        "update your RUNTIME_EXECUTION_BACKEND setting."
        % (backend_name,)
    )


def _get_backend() -> ExecutionBackend:
    global _backend
    if _backend is None:
        _backend = _build_backend()
    return _backend


def reset_execution_backend() -> None:
    """Reset cached execution backend (useful for tests)."""
    global _backend
    if _backend is not None:
        try:
            _backend.cleanup_all_sessions()
        except Exception as exc:
            logger.debug("Failed to cleanup sessions during backend reset: %s", exc)
    _backend = None
    _sessions.clear()


def create_session(
    session_id: str,
    *,
    now: datetime | None = None,
    overrides: Dict[str, object] | None = None,
) -> RuntimeSession:
    return _get_backend().create_session(session_id, now=now, overrides=overrides)


def get_session(session_id: str, *, touch: bool = True, now: datetime | None = None) -> RuntimeSession | None:
    return _get_backend().get_session(session_id, touch=touch, now=now)


def reset_session(
    session_id: str,
    *,
    now: datetime | None = None,
    overrides: Dict[str, object] | None = None,
) -> RuntimeSession:
    return _get_backend().reset_session(session_id, now=now, overrides=overrides)


def stop_session(session_id: str) -> bool:
    return _get_backend().stop_session(session_id)


def cleanup_expired(
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    *,
    now: datetime | None = None,
) -> List[str]:
    return _get_backend().cleanup_expired(ttl_seconds=ttl_seconds, now=now)


def cleanup_all_sessions() -> None:
    return _get_backend().cleanup_all_sessions()


def run_code(session_id: str, code: str) -> RuntimeExecutionResult:
    return _get_backend().run_code(session_id, code)


def run_code_stream(
    session_id: str,
    code: str,
    *,
    stdout_path: Path,
    stderr_path: Path,
) -> RuntimeExecutionResult:
    return _get_backend().run_code_stream(session_id, code, stdout_path=stdout_path, stderr_path=stderr_path)


def register_runtime_shutdown_hooks() -> None:
    global _shutdown_hooks_registered
    if _shutdown_hooks_registered:
        return
    atexit.register(cleanup_all_sessions)
    _shutdown_hooks_registered = True


register_runtime_shutdown_hooks()


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
    "run_code_stream",
    "reset_execution_backend",
    "SessionNotFoundError",
    "register_runtime_shutdown_hooks",
]
