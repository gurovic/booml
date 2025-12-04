from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Dict
import logging

from .vm_models import VirtualMachine

_AGENT_CACHE: Dict[str, VmAgent] = {}
logger = logging.getLogger(__name__)


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
    def exec_code(self, code: str) -> Dict[str, object]:
        ...

    def shutdown(self) -> None:
        """Optional hook when session resets."""
        return


class LocalVmAgent(VmAgent):
    """Legacy in-process executor for backwards compatibility."""

    def __init__(self, session):
        self.session = session

    def exec_code(self, code: str) -> Dict[str, object]:
        namespace = self.session.namespace
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        error = None
        with _workspace_cwd(self.session.workdir), redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            try:
                code = _handle_shell_commands(code, self.session.workdir, stdout_buffer, stderr_buffer, self.session.python_exec)
                if code.strip():
                    exec(code, namespace, namespace)
            except Exception:
                error = traceback.format_exc()
        return {
            "stdout": stdout_buffer.getvalue(),
            "stderr": stderr_buffer.getvalue(),
            "error": error,
            "variables": _snapshot_variables(namespace),
        }


class FilesystemVmAgent(VmAgent):
    """Communicates with the VM agent via the shared workspace directory."""

    def __init__(self, vm: VirtualMachine, *, timeout: float = 60.0):
        self.vm = vm
        self.timeout = timeout
        self.commands_dir = vm.workspace_path / ".vm_agent" / "commands"
        self.results_dir = vm.workspace_path / ".vm_agent" / "results"

    def exec_code(self, code: str) -> Dict[str, object]:
        command_id = uuid.uuid4().hex
        payload = {"code": code}
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
