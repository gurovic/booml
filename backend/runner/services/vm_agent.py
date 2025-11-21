from __future__ import annotations

import json
import os
import threading
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

from .execution_engine import ExecutionEngine
from .vm_models import VirtualMachine

_AGENT_CACHE: Dict[str, VmAgent] = {}


class VmAgent(ABC):

    @abstractmethod
    def exec_code(self, code: str) -> Dict[str, object]:
        ...

    def shutdown(self) -> None:
        return


class LocalVmAgent(VmAgent):

    def __init__(self, session):
        self.session = session
        self._ipython_lock = threading.Lock()

    def exec_code(self, code: str) -> Dict[str, Any]:
        ExecutionEngine.reset_ipython()
        
        engine = ExecutionEngine(
            workdir=self.session.workdir,
            namespace=self.session.namespace,
            session_env=self.session.env or os.environ.copy(),
            python_exec=self.session.python_exec,
            shell_lock=self._ipython_lock,
        )
        
        result = engine.execute(code)
        
        self.session.namespace = engine.namespace
        
        return result


class FilesystemVmAgent(VmAgent):

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
        except Exception:
            pass


def reset_vm_agents() -> None:
    for session_id in list(_AGENT_CACHE.keys()):
        dispose_vm_agent(session_id)


__all__ = ["get_vm_agent", "dispose_vm_agent", "reset_vm_agents"]
