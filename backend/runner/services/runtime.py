from __future__ import annotations

import builtins
import io
import os
import re
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List
import subprocess
import shutil
import venv

from django.conf import settings
from django.utils import timezone

DEFAULT_SESSION_TTL_SECONDS = 3600
DEFAULT_RUNTIME_ROOT = Path(getattr(settings, "RUNTIME_SANDBOX_ROOT", Path(settings.BASE_DIR) / "runtime_sessions"))
DEFAULT_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
_ORIGINAL_REALPATH = os.path.realpath

@dataclass
class RuntimeSession:
    namespace: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    workdir: Path
    display_path: str
    open_func: Callable[..., Any]
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


def _build_sandbox_open(workdir: Path, display_path: str):
    base_open = builtins.open
    workdir_resolved = Path(_ORIGINAL_REALPATH(str(workdir)))
    display_prefix = display_path.rstrip("/\\")

    def sandbox_open(file, *args, **kwargs):
        raw = os.fspath(file)
        path = Path(raw)
        if not path.is_absolute():
            path = Path(_ORIGINAL_REALPATH(str(workdir_resolved / path)))
        else:
            target = str(path)
            if display_prefix and (target == display_prefix or target.startswith(display_prefix + "/")):
                relative = target[len(display_prefix):].lstrip("/\\")
                relative_path = Path(relative or ".")
                path = Path(_ORIGINAL_REALPATH(str(workdir_resolved / relative_path)))
            else:
                raise PermissionError("Absolute paths are not allowed inside sandbox")
        if not str(path).startswith(str(workdir_resolved)):
            raise PermissionError("File access outside sandbox directory is not allowed")
        path.parent.mkdir(parents=True, exist_ok=True)
        return base_open(path, *args, **kwargs)

    return sandbox_open


def _new_namespace(open_func: Callable[..., Any]) -> Dict[str, Any]:
    sandbox_builtins: Dict[str, Any] = {}
    for name in dir(builtins):
        sandbox_builtins[name] = getattr(builtins, name)
    sandbox_builtins["open"] = open_func
    return {"__builtins__": sandbox_builtins}


def create_session(session_id: str, *, now: datetime | None = None) -> RuntimeSession:
    current = _resolve_now(now)
    workdir = _ensure_session_dir(session_id)
    display_path = f"/sandbox/{_sanitize_session_id(session_id)}"
    open_func = _build_sandbox_open(workdir, display_path)
    namespace = _new_namespace(open_func)
    venv_path = workdir / ".venv"
    python_exec = None
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
        display_path=display_path,
        open_func=open_func,
        python_exec=python_exec,
    )
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


class _SandboxDirEntry:
    def __init__(self, entry, sandbox: "_SandboxFilesystem"):
        self._entry = entry
        self._sandbox = sandbox

    def __getattr__(self, item: str):
        return getattr(self._entry, item)

    @property
    def path(self) -> str:
        return self._sandbox._to_display(Path(self._entry.path))

    def __fspath__(self):
        return self.path


class _SandboxFilesystem:
    def __init__(self, session: RuntimeSession):
        self.session = session
        self.root = session.workdir.resolve()
        self.display_path = session.display_path
        self.display_root = Path(self.display_path)
        self._patched: List[tuple[Any, str, Any]] = []

    def __enter__(self):
        self._patch(builtins, "open", self.session.open_func)
        self._patch(io, "open", self.session.open_func)
        self._patch_os()
        self._patch_os_path()
        self._patch_subprocess()
        self._patch_network()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        while self._patched:
            module, name, original = self._patched.pop()
            setattr(module, name, original)

    def _patch(self, module: Any, name: str, new_value: Any) -> None:
        self._patched.append((module, name, getattr(module, name)))
        setattr(module, name, new_value)

    def _resolve_path(self, value: Any, *, allow_none: bool = False):
        if value is None:
            if allow_none:
                return None
            return self.root
        if isinstance(value, int):
            return value
        raw = os.fspath(value)
        path = Path(raw)
        if path.is_absolute():
            target = str(path)
            if target.startswith(str(self.root)):
                resolved = Path(_ORIGINAL_REALPATH(target))
                if not str(resolved).startswith(str(self.root)):
                    raise PermissionError("Path outside sandbox is not allowed")
                return resolved
            prefix = self.display_path.rstrip("/\\")
            if prefix and (target == prefix or target.startswith(prefix + "/")):
                relative = target[len(prefix):].lstrip("/\\")
                path = Path(relative or ".")
            else:
                raise PermissionError("Absolute paths outside sandbox are not allowed")
        combined = self.root / path
        resolved = Path(_ORIGINAL_REALPATH(str(combined)))
        if not str(resolved).startswith(str(self.root)):
            raise PermissionError("Path outside sandbox is not allowed")
        return resolved

    def _to_display(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(self.root)
        except ValueError:
            return self.display_path
        if not relative.parts:
            return self.display_path
        return str(self.display_root.joinpath(relative))

    def _wrap_single_path(self, func):
        def wrapper(path=".", *args, **kwargs):
            resolved = self._resolve_path(path)
            return func(resolved, *args, **kwargs)
        return wrapper

    def _wrap_two_path(self, func):
        def wrapper(src, dst, *args, **kwargs):
            resolved_src = self._resolve_path(src)
            resolved_dst = self._resolve_path(dst)
            return func(resolved_src, resolved_dst, *args, **kwargs)
        return wrapper

    def _wrap_scandir(self, func):
        def wrapper(path=".", *args, **kwargs):
            resolved = self._resolve_path(path)
            for entry in func(resolved, *args, **kwargs):
                yield _SandboxDirEntry(entry, self)
        return wrapper

    def _wrap_walk(self, func):
        def wrapper(top=".", *args, **kwargs):
            resolved = self._resolve_path(top)
            for root, dirs, files in func(resolved, *args, **kwargs):
                yield self._to_display(Path(root)), dirs, files
        return wrapper

    def _block_process_call(self, message: str):
        def blocked(*_args, **_kwargs):
            raise PermissionError(message)
        return blocked

    def _patch_os(self):
        self._patch(os, "listdir", self._wrap_single_path(os.listdir))
        self._patch(os, "scandir", self._wrap_scandir(os.scandir))
        self._patch(os, "walk", self._wrap_walk(os.walk))
        self._patch(os, "remove", self._wrap_single_path(os.remove))
        self._patch(os, "unlink", self._wrap_single_path(os.unlink))
        self._patch(os, "rmdir", self._wrap_single_path(os.rmdir))
        self._patch(os, "mkdir", self._wrap_single_path(os.mkdir))
        self._patch(os, "makedirs", self._wrap_single_path(os.makedirs))
        self._patch(os, "rename", self._wrap_two_path(os.rename))
        self._patch(os, "replace", self._wrap_two_path(os.replace))
        self._patch(os, "getcwd", lambda: self.display_path)

        def blocked_chdir(*_args, **_kwargs):
            raise PermissionError("Changing working directory is not allowed inside sandbox")

        self._patch(os, "chdir", blocked_chdir)
        self._patch(os, "system", self._block_process_call("os.system is not allowed inside sandbox"))
        if hasattr(os, "popen"):
            self._patch(os, "popen", self._block_process_call("os.popen is not allowed inside sandbox"))
        for name in ("spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe"):
            if hasattr(os, name):
                self._patch(os, name, self._block_process_call("Spawning new processes is not allowed in sandbox"))
        for name in ("execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe"):
            if hasattr(os, name):
                self._patch(os, name, self._block_process_call("Executing other programs is not allowed in sandbox"))

    def _patch_os_path(self):
        return

    def _patch_subprocess(self):
        import subprocess as sp

        def blocked(*_args, **_kwargs):
            raise PermissionError("Subprocess execution is not allowed inside sandbox")

        for name in ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
            if hasattr(sp, name):
                self._patch(sp, name, blocked)

    def _patch_network(self):
        import socket as socket_module

        class _BlockedSocket:
            def __init__(self, *_args, **_kwargs):
                raise PermissionError("Network access is not allowed inside sandbox")

        blocked = self._block_process_call("Network access is not allowed inside sandbox")

        self._patch(socket_module, "socket", _BlockedSocket)
        for name in (
            "create_connection",
            "create_server",
            "fromfd",
            "socketpair",
            "gethostbyname",
            "gethostbyname_ex",
            "gethostbyaddr",
            "getaddrinfo",
            "getnameinfo",
        ):
            if hasattr(socket_module, name):
                self._patch(socket_module, name, blocked)


def run_code(session_id: str, code: str) -> RuntimeExecutionResult:
    session = _get_or_create_session(session_id)
    namespace = session.namespace

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    error: str | None = None

    with _SandboxFilesystem(session), redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
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
