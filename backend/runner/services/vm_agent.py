from __future__ import annotations

import builtins
import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Dict
import logging

from .vm_models import VirtualMachine

_AGENT_CACHE: Dict[str, VmAgent] = {}
_ACTIVE_RUNS: Dict[str, "InteractiveRun"] = {}
logger = logging.getLogger(__name__)


def _format_cell_error(code: str, exc: BaseException, file_label: str) -> str:
    lines = (code or "").splitlines()
    tb = exc.__traceback__
    lineno = None
    while tb:
        if tb.tb_frame.f_code.co_filename == "<string>":
            lineno = tb.tb_lineno
        tb = tb.tb_next
    lineno = lineno or 1
    if isinstance(exc, SyntaxError):
        if exc.lineno:
            lineno = exc.lineno
        if getattr(exc, "text", None):
            text = exc.text.rstrip("\n")
            try:
                lines[lineno - 1] = text
            except Exception:
                # If we cannot override the line (e.g. lineno out of range), fall back to
                # the original traceback formatting without modifying the source lines.
                logger.debug(
                    "Failed to apply SyntaxError text override at line %s; total lines=%s",
                    lineno,
                    len(lines),
                )
    header = [
        "---------------------------------------------------------------------------",
        f"{type(exc).__name__}                         Traceback (most recent call last)",
        f"{file_label} in <cell line: 0>()",
    ]
    start = max(1, lineno - 1)
    if start > 1 and (start - 1) <= len(lines) and lines[start - 1].strip() == "" and lineno - 2 >= 1:
        start = lineno - 2
    end = min(len(lines), lineno + 1)
    numbered = [f"{idx:>6} {lines[idx - 1]}" for idx in range(start, end + 1)]
    target_line = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
    arrow = f"{'--->':>4} {lineno} {target_line}".rstrip()
    if start <= lineno <= end:
        numbered[lineno - start] = arrow
    tail = [
        "",
        f"{type(exc).__name__}: {exc}",
    ]
    return "\n".join([*header, *numbered, *tail])


def _handle_shell_commands(code: str, workdir: Path, stdout_buffer: io.StringIO, stderr_buffer: io.StringIO, python_exec: Path | None = None) -> str:
    lines = code.split('\n')
    filtered_lines = []
    
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('!'):
            shell_cmd = stripped[1:]
            try:
                result = subprocess.run(
                    shell_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=str(workdir),
                    timeout=300,
                    env={**os.environ, 'PIP_ROOT_USER_ACTION': 'ignore'}
                )
                stdout_buffer.write(result.stdout)
                if result.stderr:
                    stderr_buffer.write(result.stderr)
            except Exception as e:
                stderr_buffer.write(f"Error executing shell command '{shell_cmd}': {str(e)}\n")
        else:
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)



class VmAgent(ABC):
    """Executes code within a VM and returns stdout/stderr/errors."""

    @abstractmethod
    def exec_code(
        self,
        code: str,
        *,
        stdin: str | None = None,
        run_id: str | None = None,
        stdin_eof: bool = False,
    ) -> Dict[str, object]:
        ...

    def shutdown(self) -> None:
        """Optional hook when session resets."""
        return


class LocalVmAgent(VmAgent):
    """Legacy in-process executor for backwards compatibility."""

    def __init__(self, session):
        self.session = session

    def exec_code(
        self,
        code: str,
        *,
        stdin: str | None = None,
        run_id: str | None = None,
        stdin_eof: bool = False,
    ) -> Dict[str, object]:
        namespace = self.session.namespace
        if run_id and run_id in _ACTIVE_RUNS:
            active_run = _ACTIVE_RUNS[run_id]
            active_run.provide_input(stdin or "", eof=stdin_eof)
            event = active_run.wait_for_event()
            result = active_run.build_result()
            if event == "finished":
                _ACTIVE_RUNS.pop(run_id, None)
            return result

        run = InteractiveRun(uuid.uuid4().hex, self.session, code)
        _ACTIVE_RUNS[run.run_id] = run
        run.start()
        event = run.wait_for_event()
        result = run.build_result()
        if event == "finished":
            _ACTIVE_RUNS.pop(run.run_id, None)
        return result


class FilesystemVmAgent(VmAgent):
    """Communicates with the VM agent via the shared workspace directory."""

    def __init__(self, vm: VirtualMachine, *, timeout: float = 60.0):
        self.vm = vm
        self.timeout = timeout
        self.commands_dir = vm.workspace_path / ".vm_agent" / "commands"
        self.results_dir = vm.workspace_path / ".vm_agent" / "results"

    def exec_code(
        self,
        code: str,
        *,
        stdin: str | None = None,
        run_id: str | None = None,
        stdin_eof: bool = False,
    ) -> Dict[str, object]:
        command_id = uuid.uuid4().hex
        payload = {"code": code, "stdin": stdin or "", "stdin_eof": stdin_eof, "run_id": run_id}
        tmp_path = self.commands_dir / f"{command_id}.json.tmp"
        final_path = self.commands_dir / f"{command_id}.json"
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(json.dumps(payload), encoding="utf-8")
        tmp_path.rename(final_path)

        result_path = self.results_dir / f"{command_id}.json"
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if result_path.exists():
                try:
                    data = json.loads(result_path.read_text(encoding="utf-8"))
                    result_path.unlink(missing_ok=True)
                    return data
                except json.JSONDecodeError:
                    pass
            time.sleep(0.05)
        raise RuntimeError("VM agent timed out waiting for execution result")


class _InteractiveStdin:
    def __init__(self, run: "InteractiveRun"):
        self._run = run

    @property
    def closed(self) -> bool:
        return self._run.closed

    def readable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return True

    def _read_from_buffer(self) -> str | None:
        if not self._run._input_buffer:
            return None
        if "\n" in self._run._input_buffer:
            line, rest = self._run._input_buffer.split("\n", 1)
            self._run._input_buffer = rest
            return f"{line}\n"
        if self._run.closed:
            data = self._run._input_buffer
            self._run._input_buffer = ""
            return data
        return None

    def readline(self, _size: int = -1) -> str:
        while True:
            chunk = self._read_from_buffer()
            if chunk is not None:
                return chunk
            if self._run.closed:
                return ""
            self._run.wait_for_input(prompt=None)

    def read(self, _size: int = -1) -> str:
        raise RuntimeError("sys.stdin.read() is not supported in this notebook runner")

    def __iter__(self):
        raise RuntimeError("Iteration over sys.stdin is not supported in this notebook runner")


class InteractiveRun:
    def __init__(self, run_id: str, session, code: str):
        self.run_id = run_id
        self.session = session
        self.code = code
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        self.error: str | None = None
        self.prompt: str | None = None
        self.status = "running"
        self.closed = False
        self._event_queue: "queue.Queue[str]" = queue.Queue()
        self._input_condition = threading.Condition()
        self._input_buffer = ""
        self._waiting_for_input = False
        self._thread = threading.Thread(target=self._execute, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def wait_for_event(self, timeout: float | None = None) -> str:
        return self._event_queue.get(timeout=timeout)

    def wait_for_input(self, prompt: str | None) -> None:
        with self._input_condition:
            self.prompt = prompt
            self.status = "input_required"
            self._waiting_for_input = True
            self._event_queue.put("input_required")
            while self._waiting_for_input and not self.closed:
                self._input_condition.wait()

    def provide_input(self, text: str, *, eof: bool = False) -> None:
        with self._input_condition:
            if eof:
                self.closed = True
            if text:
                normalized = text if text.endswith("\n") else f"{text}\n"
                self._input_buffer += normalized
            if self.prompt and not str(self.prompt).endswith("\n"):
                self._write_stdout("\n")
            self._waiting_for_input = False
            self.status = "running"
            self._input_condition.notify_all()

    def build_result(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "prompt": self.prompt,
            "run_id": self.run_id,
            "stdout": self.stdout_buffer.getvalue(),
            "stderr": self.stderr_buffer.getvalue(),
            "error": self.error,
            "variables": _snapshot_variables(self.session.namespace),
        }

    def _write_stdout(self, text: str) -> None:
        if text:
            self.stdout_buffer.write(text)

    def _execute(self) -> None:
        namespace = self.session.namespace
        original_stdin = sys.stdin
        original_input = builtins.input
        try:
            sys.stdin = _InteractiveStdin(self)

            def _input(prompt: str = "") -> str:
                if prompt:
                    self._write_stdout(prompt)
                self.wait_for_input(prompt or "")
                line = sys.stdin.readline()
                return line.rstrip("\n")

            builtins.input = _input

            try:
                import fileinput as _fileinput

                def _blocked_fileinput(*_args, **_kwargs):
                    raise RuntimeError("fileinput.input() is not supported in this notebook runner")

                _fileinput.input = _blocked_fileinput
            except Exception:
                # Best-effort: if disabling fileinput fails, continue execution but log for debugging.
                logger.debug("Failed to disable fileinput.input() in notebook runner", exc_info=True)

            with _workspace_cwd(self.session.workdir), redirect_stdout(self.stdout_buffer), redirect_stderr(self.stderr_buffer):
                filtered_code = _handle_shell_commands(
                    self.code,
                    self.session.workdir,
                    self.stdout_buffer,
                    self.stderr_buffer,
                    self.session.python_exec,
                )
                if filtered_code.strip():
                    exec(filtered_code, namespace, namespace)
        except Exception as exc:
            self.error = _format_cell_error(self.code, exc, "<string>")
        finally:
            builtins.input = original_input
            sys.stdin = original_stdin
            self.status = "error" if self.error else "success"
            self._event_queue.put("finished")


def get_vm_agent(session_id: str, session) -> VmAgent:
    agent = _AGENT_CACHE.get(session_id)
    if agent is not None:
        return agent
    vm = session.vm
    if vm and vm.backend == "docker":
        agent = FilesystemVmAgent(vm)
    else:
        agent = LocalVmAgent(session)
    _AGENT_CACHE[session_id] = agent
    return agent


def dispose_vm_agent(session_id: str) -> None:
    agent = _AGENT_CACHE.pop(session_id, None)
    if agent:
        try:
            agent.shutdown()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to shutdown VM agent %s: %s", session_id, exc)


def reset_vm_agents() -> None:
    for session_id in list(_AGENT_CACHE.keys()):
        dispose_vm_agent(session_id)


def _snapshot_variables(namespace: Dict[str, object]) -> Dict[str, str]:
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


@contextmanager
def _workspace_cwd(path: Path):
    original = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


__all__ = ["get_vm_agent", "dispose_vm_agent", "reset_vm_agents"]
