from __future__ import annotations

import builtins
import io
import os
import re
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List
import shutil
import venv
from urllib.parse import urlparse
from urllib.request import urlopen

from django.conf import settings
from django.utils import timezone

DEFAULT_SESSION_TTL_SECONDS = 3600
DEFAULT_RUNTIME_ROOT = Path(getattr(settings, "RUNTIME_SANDBOX_ROOT", Path(settings.BASE_DIR) / "runtime_sessions"))
DEFAULT_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
_ORIGINAL_REALPATH = os.path.realpath
BLOCKED_IMPORTS = {"ctypes", "cffi", "multiprocessing"}
_DOWNLOAD_CONTEXT = ContextVar("runtime_download_active", default=False)


def _normalize_allowed_type(value: str | None) -> str | None:
    if not value:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    if normalized.startswith("."):
        normalized = normalized[1:]
    return normalized or None


_ALLOWED_DOWNLOAD_TYPES = tuple(
    sorted(
        {
            normalized
            for normalized in (
                _normalize_allowed_type(entry)
                for entry in getattr(settings, "RUNTIME_ALLOWED_DOWNLOAD_TYPES", [])
            )
            if normalized
        }
    )
    or ("csv", "json", "txt")
)

_ALLOWED_TYPES_LABEL = ", ".join(_ALLOWED_DOWNLOAD_TYPES)


def _iter_suffix_candidates(name: str) -> List[str]:
    path = Path(name.lower().strip())
    suffixes = [suffix[1:] for suffix in path.suffixes if suffix]
    candidates: set[str] = set()
    for index, suffix in enumerate(suffixes):
        if suffix:
            candidates.add(suffix)
        combined = ".".join(filter(None, suffixes[index:]))
        if combined:
            candidates.add(combined)
    return list(candidates)


def _is_extension_allowed(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    lowered = filename.lower()
    if any(lowered.endswith(f".{ext}") for ext in _ALLOWED_DOWNLOAD_TYPES):
        return True
    for candidate in _iter_suffix_candidates(filename):
        if candidate in _ALLOWED_DOWNLOAD_TYPES:
            return True
    return False


def _ensure_allowed_extension(filename: str) -> None:
    if not _is_extension_allowed(filename):
        raise PermissionError(
            "Создание файлов с таким расширением запрещено в песочнице. "
            f"Разрешённые расширения: {_ALLOWED_TYPES_LABEL or 'недоступно'}"
        )


def _is_write_mode(mode: Any) -> bool:
    if not isinstance(mode, str):
        mode = "r"
    normalized = mode or "r"
    return any(flag in normalized for flag in ("w", "a", "x", "+"))


def _ensure_allowed_file_path(path: Path) -> None:
    try:
        if path.exists() and path.is_dir():
            return
    except OSError:
        pass
    _ensure_allowed_extension(path.name)

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
        mode = kwargs.get("mode")
        if len(args) >= 1:
            mode = args[0]
        if _is_write_mode(mode or "r"):
            _ensure_allowed_file_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return base_open(path, *args, **kwargs)

    return sandbox_open


def _sanitize_relative_path(value: str) -> Path:
    candidate = Path(str(value).strip())
    parts: list[str] = []
    for part in candidate.parts:
        if not part or part == ".":
            continue
        if part == "..":
            raise ValueError("Parent directory references are not allowed inside sandbox")
        parts.append(part)
    if not parts:
        raise ValueError("Filename is required")
    normalized = Path(*parts)
    if len(str(normalized)) > 240:
        raise ValueError("Target path is too long")
    return normalized


def _derive_default_filename(parsed_path: str) -> str:
    tail = Path(parsed_path or "").name
    if tail:
        return tail
    return "downloaded.file"


def _build_download_helper(session: RuntimeSession):
    def download_file(url: str, *, filename: str | None = None, chunk_size: int = 1024 * 1024) -> str:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("URL must be a non-empty string")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only HTTP/HTTPS downloads are supported inside sandbox")

        remote_name = Path(parsed.path or "").name
        if remote_name and "." in remote_name:
            _ensure_allowed_extension(remote_name)

        target_name = filename or remote_name or _derive_default_filename(parsed.path)
        _ensure_allowed_extension(target_name)
        target_path = _sanitize_relative_path(target_name)

        chunk = int(chunk_size or 0)
        if chunk <= 0 or chunk > 32 * 1024 * 1024:
            raise ValueError("chunk_size must be between 1 and 32 MiB")

        relative_str = str(target_path)
        token = _DOWNLOAD_CONTEXT.set(True)
        try:
            with urlopen(url) as response, session.open_func(relative_str, "wb") as destination:
                while True:
                    data = response.read(chunk)
                    if not data:
                        break
                    destination.write(data)
        finally:
            _DOWNLOAD_CONTEXT.reset(token)
        return relative_str

    download_file.__name__ = "download_file"
    download_file.__doc__ = (
        "download_file(url, filename=None, chunk_size=1048576)\n"
        "Загружает файл разрешённого типа напрямую в директорию текущей сессии "
        "и возвращает относительный путь."
    )
    return download_file


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
    session.namespace["download_file"] = _build_download_helper(session)
    session.namespace["allowed_download_types"] = _ALLOWED_DOWNLOAD_TYPES
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
        self._patch_imports()
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

    def _ensure_destination_allowed(self, resolved_src, resolved_dst, *, allow_dirs: bool) -> None:
        if allow_dirs:
            try:
                if Path(resolved_src).is_dir():
                    return
            except OSError:
                pass
        _ensure_allowed_file_path(Path(resolved_dst))

    def _wrap_checked_two_path(self, func, *, allow_dirs: bool):
        def wrapper(src, dst, *args, **kwargs):
            resolved_src = self._resolve_path(src)
            resolved_dst = self._resolve_path(dst)
            self._ensure_destination_allowed(resolved_src, resolved_dst, allow_dirs=allow_dirs)
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

    def _wrap_os_open(self, func):
        def wrapper(path, flags, *args, **kwargs):
            resolved = self._resolve_path(path)
            write_flags = 0
            for name in ("O_WRONLY", "O_RDWR", "O_APPEND", "O_CREAT", "O_TRUNC"):
                write_flags |= getattr(os, name, 0)
            if flags & write_flags:
                _ensure_allowed_file_path(Path(resolved))
            return func(resolved, flags, *args, **kwargs)
        return wrapper

    def _wrap_readlink(self, func):
        def wrapper(path, *args, **kwargs):
            resolved = self._resolve_path(path)
            result = func(resolved, *args, **kwargs)
            return self._to_display(Path(result))
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
        self._patch(os, "rename", self._wrap_checked_two_path(os.rename, allow_dirs=True))
        self._patch(os, "replace", self._wrap_checked_two_path(os.replace, allow_dirs=True))
        if hasattr(os, "symlink"):
            self._patch(os, "symlink", self._wrap_checked_two_path(os.symlink, allow_dirs=False))
        if hasattr(os, "link"):
            self._patch(os, "link", self._wrap_checked_two_path(os.link, allow_dirs=False))
        if hasattr(os, "readlink"):
            self._patch(os, "readlink", self._wrap_readlink(os.readlink))
        if hasattr(os, "open"):
            self._patch(os, "open", self._wrap_os_open(os.open))
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

    def _patch_imports(self):
        for module_name in list(sys.modules.keys()):
            root = module_name.split(".")[0]
            if root in BLOCKED_IMPORTS:
                sys.modules.pop(module_name, None)

        original_import = builtins.__import__

        def sandbox_import(name, globals=None, locals=None, fromlist=(), level=0):
            root = name.split(".")[0]
            if root in BLOCKED_IMPORTS:
                raise PermissionError(f"Importing module '{root}' is not allowed inside sandbox")
            return original_import(name, globals, locals, fromlist, level)

        self._patch(builtins, "__import__", sandbox_import)

    def _patch_network(self):
        import socket as socket_module

        original_socket_cls = socket_module.socket

        def _require_download_access(action: str = "Network access") -> None:
            if not _DOWNLOAD_CONTEXT.get():
                raise PermissionError(f"{action} is only allowed via download_file() inside sandbox")

        class SandboxSocket(original_socket_cls):
            def __init__(self, *args, **kwargs):
                _require_download_access()
                fileno = kwargs.get("fileno")
                if len(args) >= 4:
                    fileno = args[3]
                if fileno is not None:
                    raise PermissionError("Reusing existing sockets is not allowed inside sandbox")
                family = args[0] if args else kwargs.get("family", socket_module.AF_INET)
                if family not in (socket_module.AF_INET, socket_module.AF_INET6):
                    raise PermissionError("Only AF_INET/AF_INET6 sockets are allowed inside sandbox")
                kind = args[1] if len(args) > 1 else kwargs.get("type", socket_module.SOCK_STREAM)
                if kind != socket_module.SOCK_STREAM:
                    raise PermissionError("Only TCP client sockets are allowed inside sandbox")
                super().__init__(*args, **kwargs)

            def connect(self, address):
                _require_download_access()
                return super().connect(address)

            def connect_ex(self, address):
                _require_download_access()
                return super().connect_ex(address)

            def bind(self, *_args, **_kwargs):
                raise PermissionError("Binding sockets is not allowed inside sandbox")

            def listen(self, *_args, **_kwargs):
                raise PermissionError("Listening sockets is not allowed inside sandbox")

            def accept(self, *_args, **_kwargs):
                raise PermissionError("Accepting sockets is not allowed inside sandbox")

        SandboxSocket.__name__ = "SandboxSocket"
        self._patch(socket_module, "socket", SandboxSocket)

        def wrap_create_connection(func):
            def inner(address, *args, **kwargs):
                _require_download_access()
                return func(address, *args, **kwargs)
            return inner

        if hasattr(socket_module, "create_connection"):
            self._patch(socket_module, "create_connection", wrap_create_connection(socket_module.create_connection))

        blocked_server = self._block_process_call("Server sockets are not allowed inside sandbox")
        for name in ("create_server", "fromfd", "socketpair"):
            if hasattr(socket_module, name):
                self._patch(socket_module, name, blocked_server)

        def wrap_lookup(func):
            def inner(host, *args, **kwargs):
                _require_download_access()
                return func(host, *args, **kwargs)
            return inner

        for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex"):
            if hasattr(socket_module, name):
                self._patch(socket_module, name, wrap_lookup(getattr(socket_module, name)))

        if hasattr(socket_module, "getnameinfo"):
            self._patch(
                socket_module,
                "getnameinfo",
                self._block_process_call("Reverse DNS lookups are not allowed inside sandbox"),
            )

        if hasattr(socket_module, "gethostbyaddr"):
            self._patch(
                socket_module,
                "gethostbyaddr",
                self._block_process_call("Reverse DNS lookups are not allowed inside sandbox"),
            )


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
