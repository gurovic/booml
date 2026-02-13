from __future__ import annotations

import ast
import atexit
import builtins
import io
import logging
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from queue import Empty
from typing import Any, Dict, List

import venv
from urllib.parse import urlparse
from urllib.request import urlopen

from django.conf import settings
from django.utils import timezone

from .vm_agent import (
    _handle_shell_commands,
    dispose_vm_agent,
    get_vm_agent,
    get_interactive_run,
    provide_interactive_input,
    start_interactive_run,
)
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
    status: str = "success"
    prompt: str | None = None
    run_id: str | None = None


def _build_execution_result(payload: Dict[str, object]) -> RuntimeExecutionResult:
    return RuntimeExecutionResult(
        stdout=str(payload.get("stdout") or ""),
        stderr=str(payload.get("stderr") or ""),
        error=payload.get("error"),
        variables=payload.get("variables") or {},
        outputs=payload.get("outputs") or [],
        artifacts=payload.get("artifacts") or [],
        status=str(payload.get("status") or "success"),
        prompt=payload.get("prompt"),
        run_id=payload.get("run_id"),
    )


@dataclass
class _KernelContext:
    manager: Any
    client: Any
    python_exec: Path | None


@dataclass
class _KernelResult:
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


def _open_stream_file(path: Path) -> io.TextIOBase | None:
    if not path:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.open("a", encoding="utf-8")
    except Exception:
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

    def provide_input(
        self,
        session_id: str,
        run_id: str,
        text: str | None,
        *,
        stdin_eof: bool = False,
    ) -> RuntimeExecutionResult:  # pragma: no cover - abstract
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
        run_id = uuid.uuid4().hex
        vm = session.vm
        if vm and vm.backend == "docker":
            agent = get_vm_agent(session_id, session)
            if hasattr(agent, "exec_interactive_start"):
                result_payload = agent.exec_interactive_start(code, run_id=run_id)
            else:
                result_payload = agent.exec_code(code)
        else:
            run = start_interactive_run(session=session, code=code, run_id=run_id)
            run.wait_for_status()
            result_payload = run.to_payload()
        session.updated_at = _resolve_now()
        return _build_execution_result(result_payload)

    def provide_input(
        self,
        session_id: str,
        run_id: str,
        text: str | None,
        *,
        stdin_eof: bool = False,
    ) -> RuntimeExecutionResult:
        session = self._require_session(session_id)
        vm = session.vm
        if vm and vm.backend == "docker":
            agent = get_vm_agent(session_id, session)
            if hasattr(agent, "exec_interactive_input"):
                result_payload = agent.exec_interactive_input(run_id, text, stdin_eof=stdin_eof)
            else:
                result_payload = {
                    "status": "error",
                    "prompt": None,
                    "run_id": run_id,
                    "stdout": "",
                    "stderr": "",
                    "error": "Interactive input is not supported by the VM agent",
                    "variables": {},
                    "outputs": [],
                    "artifacts": [],
                }
        else:
            run = get_interactive_run(run_id)
            if run is None:
                result_payload = {
                    "status": "error",
                    "prompt": None,
                    "run_id": run_id,
                    "stdout": "",
                    "stderr": "",
                    "error": "Interactive run not found",
                    "variables": {},
                    "outputs": [],
                    "artifacts": [],
                }
            else:
                seq = run.status_seq
                provide_interactive_input(run_id, text, stdin_eof=stdin_eof)
                run.wait_for_status(since_seq=seq)
                result_payload = run.to_payload()
        session.updated_at = _resolve_now()
        return _build_execution_result(result_payload)

    def run_code_stream(
        self,
        session_id: str,
        code: str,
        *,
        stdout_path: Path,
        stderr_path: Path,
    ) -> RuntimeExecutionResult:
        session = self._require_session(session_id)
        vm = session.vm
        if vm and vm.backend == "docker":
            agent = get_vm_agent(session_id, session)
            result_payload = agent.exec_code_stream(code, stdout_path=stdout_path, stderr_path=stderr_path)
        else:
            agent = get_vm_agent(session_id, session)
            result_payload = agent.exec_code_stream(code, stdout_path=stdout_path, stderr_path=stderr_path)
        session.updated_at = _resolve_now()
        return _build_execution_result(result_payload)


class JupyterExecutionBackend(ExecutionBackend):
    """Executes code inside a persistent Jupyter kernel per session."""

    def __init__(self, *, sessions: Dict[str, RuntimeSession]):
        super().__init__(sessions=sessions)
        self._kernels: Dict[str, _KernelContext] = {}
        self.startup_timeout = 30.0
        self.shell_timeout = 30.0
        self.iopub_timeout = 30.0

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
        python_exec: Path | None = None
        if vm.backend == "local":
            python_exec = _prepare_local_python_exec(workdir)

        session = RuntimeSession(
            namespace={},
            created_at=current,
            updated_at=current,
            workdir=workdir,
            python_exec=python_exec,
            vm=vm,
        )
        self.sessions[session_id] = session
        try:
            self._start_kernel(session_id, session)
        except Exception:
            self.sessions.pop(session_id, None)
            _destroy_session_vm(session_id)
            raise
        return session

    def stop_session(self, session_id: str) -> bool:
        session = self.sessions.pop(session_id, None)
        self._shutdown_kernel(session_id)
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
        vm = session.vm
        if vm and vm.backend == "docker":
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

        kernel = self._ensure_kernel(session_id, session)
        effective_code = code if code.strip() else "pass"
        kernel_result = self._execute_in_kernel(kernel, effective_code)
        session.updated_at = _resolve_now()

        return RuntimeExecutionResult(
            stdout=kernel_result.stdout,
            stderr=kernel_result.stderr,
            error=kernel_result.error,
            variables=kernel_result.variables,
            outputs=kernel_result.outputs,
            artifacts=kernel_result.artifacts,
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
        vm = session.vm
        if vm and vm.backend == "docker":
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

        kernel = self._ensure_kernel(session_id, session)
        effective_code = code if code.strip() else "pass"
        stdout_stream = _open_stream_file(stdout_path)
        stderr_stream = _open_stream_file(stderr_path)
        try:
            kernel_result = self._execute_request(
                kernel.client,
                effective_code,
                capture_vars=True,
                stdout_stream=stdout_stream,
                stderr_stream=stderr_stream,
            )
        finally:
            if stdout_stream:
                stdout_stream.close()
            if stderr_stream:
                stderr_stream.close()
        session.updated_at = _resolve_now()

        return RuntimeExecutionResult(
            stdout=kernel_result.stdout,
            stderr=kernel_result.stderr,
            error=kernel_result.error,
            variables=kernel_result.variables,
            outputs=kernel_result.outputs,
            artifacts=kernel_result.artifacts,
        )

    def provide_input(
        self,
        session_id: str,
        run_id: str,
        text: str | None,
        *,
        stdin_eof: bool = False,
    ) -> RuntimeExecutionResult:
        raise RuntimeError("Interactive input is not supported by the Jupyter backend")

    # --- kernel lifecycle -------------------------------------------------

    def _ensure_kernel(self, session_id: str, session: RuntimeSession) -> _KernelContext:
        kernel = self._kernels.get(session_id)
        if kernel is not None:
            return kernel
        self._start_kernel(session_id, session)
        kernel = self._kernels.get(session_id)
        if kernel is None:
            raise SessionNotFoundError(f"Kernel for session '{session_id}' is not available")
        return kernel

    def _start_kernel(self, session_id: str, session: RuntimeSession) -> None:
        try:
            from jupyter_client import KernelManager
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Jupyter backend requires jupyter_client to be installed: {exc}") from exc

        kernel_cmd = None
        env = os.environ.copy()
        if session.python_exec:
            env["VIRTUAL_ENV"] = str(session.python_exec.parent.parent)
            env["PATH"] = f"{session.python_exec.parent}{os.pathsep}{env.get('PATH', '')}"
            kernel_cmd = [str(session.python_exec), "-m", "ipykernel_launcher", "-f", "{connection_file}"]

        manager = KernelManager(kernel_cmd=kernel_cmd)
        client = None
        used_python = session.python_exec
        try:
            manager.start_kernel(cwd=str(session.workdir), env=env)
            client = manager.client()
            client.start_channels()
            client.wait_for_ready(timeout=self.startup_timeout)
            self._initialize_kernel(client, session.workdir)
            self._kernels[session_id] = _KernelContext(manager=manager, client=client, python_exec=used_python)
            return
        except Exception as exc:
            self._terminate_kernel_process(client, manager)
            if kernel_cmd is not None:
                logger.warning(
                    "Failed to start Jupyter kernel with %s, retrying with default interpreter: %s",
                    session.python_exec,
                    exc,
                )
                fallback_manager = KernelManager()
                fallback_client = None
                try:
                    fallback_manager.start_kernel(cwd=str(session.workdir), env=env)
                    fallback_client = fallback_manager.client()
                    fallback_client.start_channels()
                    fallback_client.wait_for_ready(timeout=self.startup_timeout)
                    self._initialize_kernel(fallback_client, session.workdir)
                    used_python = None
                    self._kernels[session_id] = _KernelContext(
                        manager=fallback_manager,
                        client=fallback_client,
                        python_exec=used_python,
                    )
                    return
                except Exception:
                    self._terminate_kernel_process(fallback_client, fallback_manager)
            raise

    def _shutdown_kernel(self, session_id: str) -> None:
        context = self._kernels.pop(session_id, None)
        if not context:
            return
        self._terminate_kernel_process(context.client, context.manager)

    def _terminate_kernel_process(self, client: Any | None, manager: Any | None) -> None:
        try:
            if client:
                client.stop_channels()
        except Exception as exc:
            logger.debug("Failed to stop kernel client channels: %s", exc)
        try:
            if manager:
                manager.shutdown_kernel(now=True)
        except Exception as exc:
            logger.debug("Failed to shutdown kernel manager: %s", exc)

    # --- kernel execution helpers ----------------------------------------

    def _initialize_kernel(self, client, workdir: Path) -> None:
        init_code = """
import os
from pathlib import Path as _Path
import json as _json
import builtins as __builtins__
from urllib.request import urlopen as _urlopen
from urllib.parse import urlparse as _urlparse

__name__ = "__main__"
os.chdir(r"__WORKDIR__")
_workdir = _Path(r"__WORKDIR__")

def download_file(url, *, filename=None, chunk_size=1024 * 1024, timeout=30.0):
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL must be a non-empty string")
    parsed = _urlparse(url)
    basename = _Path(parsed.path or "").name
    target_name = filename or basename or "downloaded.file"
    target_path = _workdir / target_name
    target_path.parent.mkdir(parents=True, exist_ok=True)
    size = int(chunk_size or 0)
    if size <= 0:
        size = 1024 * 1024
    with _urlopen(url, timeout=timeout) as response, target_path.open("wb") as destination:
        while True:
            data = response.read(size)
            if not data:
                break
            destination.write(data)
    return str(target_path.relative_to(_workdir))


def _booml_snapshot_vars():
    result = {}
    for key, value in globals().items():
        if key == "__builtins__":
            continue
        if key.startswith("__") and key.endswith("__"):
            continue
        try:
            result[key] = repr(value)
        except Exception:
            try:
                name = getattr(value, "__class__", type(value)).__name__
            except Exception:
                name = "object"
            result[key] = "<unrepresentable {}>".format(name)
    return result
""".replace("__WORKDIR__", str(workdir))
        self._execute_request(client, init_code, capture_vars=False)

    def _execute_in_kernel(self, kernel: _KernelContext, code: str) -> _KernelResult:
        return self._execute_request(kernel.client, code, capture_vars=True)

    def _execute_request(
        self,
        client,
        code: str,
        *,
        capture_vars: bool,
        stdout_stream: io.TextIOBase | None = None,
        stderr_stream: io.TextIOBase | None = None,
    ) -> _KernelResult:
        user_expressions = {"__booml_vars": "_booml_snapshot_vars()"} if capture_vars else {}
        msg_id = client.execute(
            code,
            store_history=False,
            allow_stdin=False,
            stop_on_error=False,
            user_expressions=user_expressions,
        )
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        error_text: str | None = None

        while True:
            try:
                msg = client.get_iopub_msg(timeout=self.iopub_timeout)
            except Empty as exc:
                raise TimeoutError("Jupyter kernel did not respond in time") from exc
            if msg.get("parent_header", {}).get("msg_id") != msg_id:
                continue
            msg_type = msg.get("msg_type")
            content = msg.get("content", {})
            if msg_type == "stream":
                name = content.get("name")
                text = content.get("text", "")
                if name == "stdout":
                    stdout_parts.append(text)
                    if stdout_stream:
                        stdout_stream.write(text)
                        stdout_stream.flush()
                elif name == "stderr":
                    stderr_parts.append(text)
                    if stderr_stream:
                        stderr_stream.write(text)
                        stderr_stream.flush()
            elif msg_type == "error":
                trace = content.get("traceback") or []
                error_text = "\n".join(trace) or f"{content.get('ename')}: {content.get('evalue')}"
            elif msg_type == "status" and content.get("execution_state") == "idle":
                break

        reply = self._wait_for_reply(client, msg_id)
        reply_content = reply.get("content", {}) if reply else {}
        if error_text is None and reply_content.get("status") == "error":
            trace = reply_content.get("traceback") or []
            error_text = "\n".join(trace) or f"{reply_content.get('ename')}: {reply_content.get('evalue')}"

        variables: Dict[str, str] = {}
        if capture_vars:
            variables = self._parse_variables(reply_content)

        return _KernelResult(
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
            error=error_text,
            variables=variables,
            outputs=[],
            artifacts=[],
        )

    def _wait_for_reply(self, client, msg_id: str) -> dict:
        while True:
            try:
                reply = client.get_shell_msg(timeout=self.shell_timeout)
            except Empty as exc:  # pragma: no cover - defensive
                raise TimeoutError("Jupyter kernel did not send execute reply") from exc
            if reply.get("parent_header", {}).get("msg_id") == msg_id:
                return reply

    def _parse_variables(self, reply_content: dict) -> Dict[str, str]:
        expressions = reply_content.get("user_expressions") or {}
        payload = expressions.get("__booml_vars") or {}
        if payload.get("status") != "ok":
            return {}
        data = payload.get("data") or {}
        raw = data.get("text/plain", "")
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, dict):
                return {str(key): str(value) for key, value in parsed.items()}
        except Exception:
            logger.debug("Failed to parse variable snapshot from kernel", exc_info=True)
        return {}


def _build_backend() -> ExecutionBackend:
    backend_name = (
        str(getattr(settings, "RUNTIME_EXECUTION_BACKEND", os.environ.get("RUNTIME_EXECUTION_BACKEND", "legacy")) or "legacy")
        .strip()
        .lower()
    )
    # Treat empty/default/legacy strings as legacy for backward compatibility.
    if backend_name in ("", "legacy", "default"):
        return LegacyExecutionBackend(sessions=_sessions)
    if backend_name == "jupyter":
        return JupyterExecutionBackend(sessions=_sessions)
    raise ValueError(f"Unsupported execution backend: {backend_name!r}")


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


def provide_input(
    session_id: str,
    run_id: str,
    text: str | None,
    *,
    stdin_eof: bool = False,
) -> RuntimeExecutionResult:
    return _get_backend().provide_input(session_id, run_id, text, stdin_eof=stdin_eof)


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
