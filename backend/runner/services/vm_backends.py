from __future__ import annotations

import json
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from django.utils import timezone

from .vm_agent_server import VM_AGENT_SERVER_SOURCE
from .vm_exceptions import VmAlreadyExistsError, VmNotFoundError
from .vm_models import (
    VirtualMachine,
    VirtualMachineState,
    VmNetworkPolicy,
    VmResources,
    VmSpec,
)


class VmBackend(ABC):
    """Abstract interface describing VM lifecycle operations."""

    @abstractmethod
    def create_vm(
        self,
        *,
        vm_id: str,
        session_id: str,
        spec: VmSpec,
        now: datetime | None = None,
    ) -> VirtualMachine:
        ...

    @abstractmethod
    def get_vm(self, vm_id: str) -> VirtualMachine:
        ...

    @abstractmethod
    def delete_vm(self, vm_id: str) -> None:
        ...


class LocalVmBackend(VmBackend):
    """Stores VM metadata on the local filesystem (legacy sandbox)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create_vm(
        self,
        *,
        vm_id: str,
        session_id: str,
        spec: VmSpec,
        now: datetime | None = None,
    ) -> VirtualMachine:
        vm_dir = self._vm_dir(vm_id)
        if vm_dir.exists():
            # If directory exists but no metadata, it's a stale state - clean it up
            metadata_path = self._metadata_path(vm_dir)
            if not metadata_path.exists():
                shutil.rmtree(vm_dir, ignore_errors=True)
            else:
                raise VmAlreadyExistsError(f"VM {vm_id} already exists at {vm_dir}")

        vm_dir.mkdir(parents=True, exist_ok=False)
        workspace = vm_dir / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        timestamp = _resolve_now(now)
        vm = VirtualMachine(
            id=vm_id,
            session_id=session_id,
            spec=spec,
            state=VirtualMachineState.RUNNING,
            workspace_path=workspace,
            created_at=timestamp,
            updated_at=timestamp,
            backend="local",
            backend_data={},
        )
        self._write_metadata(vm_dir, vm)
        return vm

    def get_vm(self, vm_id: str) -> VirtualMachine:
        vm_dir = self._vm_dir(vm_id)
        if not vm_dir.exists():
            raise VmNotFoundError(f"VM {vm_id} was not found under {self.root}")
        # If directory exists but no metadata, it's a stale state - clean it up and re-raise
        metadata_path = self._metadata_path(vm_dir)
        if not metadata_path.exists():
            shutil.rmtree(vm_dir, ignore_errors=True)
            raise VmNotFoundError(f"Metadata is missing for VM at {vm_dir}")
        return self._read_metadata(vm_dir)

    def delete_vm(self, vm_id: str) -> None:
        vm_dir = self._vm_dir(vm_id)
        if not vm_dir.exists():
            raise VmNotFoundError(f"VM {vm_id} was not found under {self.root}")
        shutil.rmtree(vm_dir, ignore_errors=True)

    def _vm_dir(self, vm_id: str) -> Path:
        return self.root / vm_id

    def _metadata_path(self, vm_dir: Path) -> Path:
        return vm_dir / "metadata.json"

    def _write_metadata(self, vm_dir: Path, vm: VirtualMachine) -> None:
        payload = self._serialize_vm(vm)
        metadata_path = self._metadata_path(vm_dir)
        metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _read_metadata(self, vm_dir: Path) -> VirtualMachine:
        metadata_path = self._metadata_path(vm_dir)
        if not metadata_path.exists():
            raise VmNotFoundError(f"Metadata is missing for VM at {vm_dir}")
        payload = json.loads(metadata_path.read_text())
        return self._deserialize_vm(payload, vm_dir)

    def _serialize_vm(self, vm: VirtualMachine) -> Dict[str, Any]:
        spec_dict = asdict(vm.spec)
        spec_dict["network"]["allowlist"] = list(spec_dict["network"]["allowlist"])
        return {
            "vm_id": vm.id,
            "session_id": vm.session_id,
            "state": vm.state.value,
            "spec": spec_dict,
            "workspace_path": str(vm.workspace_path),
            "created_at": vm.created_at.isoformat(),
            "updated_at": vm.updated_at.isoformat(),
            "backend": vm.backend,
            "backend_data": vm.backend_data,
        }

    def _deserialize_vm(self, payload: Dict[str, Any], vm_dir: Path) -> VirtualMachine:
        spec_payload = payload["spec"]
        resources = VmResources(**spec_payload["resources"])
        network_payload = spec_payload["network"]
        network = VmNetworkPolicy(
            outbound=network_payload["outbound"],
            allowlist=tuple(network_payload.get("allowlist", ())),
        )
        spec = VmSpec(
            image=spec_payload["image"],
            resources=resources,
            network=network,
            ttl_sec=spec_payload["ttl_sec"],
        )
        workspace_path = Path(payload.get("workspace_path") or (vm_dir / "workspace"))
        backend_data = payload.get("backend_data") or {}
        return VirtualMachine(
            id=payload["vm_id"],
            session_id=payload["session_id"],
            spec=spec,
            state=VirtualMachineState(payload["state"]),
            workspace_path=workspace_path,
            created_at=datetime.fromisoformat(payload["created_at"]),
            updated_at=datetime.fromisoformat(payload["updated_at"]),
            backend=payload.get("backend", "local"),
            backend_data=backend_data,
        )


class DockerVmBackend(VmBackend):
    """Provision VMs as long-lived Docker containers with a workspace mount."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create_vm(
        self,
        *,
        vm_id: str,
        session_id: str,
        spec: VmSpec,
        now: datetime | None = None,
    ) -> VirtualMachine:
        vm_dir = self._vm_dir(vm_id)
        if vm_dir.exists():
            # If directory exists but no metadata, it's a stale state - clean it up
            metadata_path = self._metadata_path(vm_dir)
            if not metadata_path.exists():
                shutil.rmtree(vm_dir, ignore_errors=True)
            else:
                raise VmAlreadyExistsError(f"VM {vm_id} already exists at {vm_dir}")
        
        vm_dir.mkdir(parents=True, exist_ok=False)

        workspace = vm_dir / "workspace"
        agent_dir = self._prepare_agent_dir(workspace)
        timestamp = _resolve_now(now)

        container_name = vm_id
        try:
            self._create_container(container_name, spec, vm_dir, workspace)
            self._start_agent(container_name)
            self._wait_for_agent(agent_dir)
        except Exception:
            shutil.rmtree(vm_dir, ignore_errors=True)
            raise

        vm = VirtualMachine(
            id=vm_id,
            session_id=session_id,
            spec=spec,
            state=VirtualMachineState.RUNNING,
            workspace_path=workspace,
            created_at=timestamp,
            updated_at=timestamp,
            backend="docker",
            backend_data={"container": container_name},
        )
        self._write_metadata(vm_dir, vm)
        return vm

    def get_vm(self, vm_id: str) -> VirtualMachine:
        vm_dir = self._vm_dir(vm_id)
        if not vm_dir.exists():
            raise VmNotFoundError(f"VM {vm_id} was not found under {self.root}")
        # If directory exists but no metadata, it's a stale state - clean it up and re-raise
        metadata_path = self._metadata_path(vm_dir)
        if not metadata_path.exists():
            container = self._read_container_name(vm_dir)
            if container:
                self._run_docker(("rm", "-f", container), check=False)
            shutil.rmtree(vm_dir, ignore_errors=True)
            raise VmNotFoundError(f"Metadata is missing for VM at {vm_dir}")
        return self._read_metadata(vm_dir)

    def delete_vm(self, vm_id: str) -> None:
        vm_dir = self._vm_dir(vm_id)
        if not vm_dir.exists():
            raise VmNotFoundError(f"VM {vm_id} was not found under {self.root}")
        container = self._read_container_name(vm_dir)
        if container:
            self._run_docker(("rm", "-f", container), check=False)
        shutil.rmtree(vm_dir, ignore_errors=True)

    # --- internal helpers -------------------------------------------------

    def _prepare_agent_dir(self, workspace: Path) -> Path:
        workspace.mkdir(parents=True, exist_ok=True)
        agent_root = workspace / ".vm_agent"
        commands_dir = agent_root / "commands"
        results_dir = agent_root / "results"
        logs_dir = agent_root / "logs"
        for directory in (agent_root, commands_dir, results_dir, logs_dir):
            directory.mkdir(parents=True, exist_ok=True)
        agent_file = agent_root / "agent_server.py"
        agent_file.write_text(VM_AGENT_SERVER_SOURCE)
        return agent_root

    def _create_container(
        self,
        container_name: str,
        spec: VmSpec,
        vm_dir: Path,
        workspace: Path,
    ) -> None:
        args = [
            "create",
            "--name",
            container_name,
            "--hostname",
            container_name,
            "--cpus",
            str(spec.resources.cpu),
            "--memory",
            f"{spec.resources.ram_mb}m",
            "--pids-limit",
            "512",
            "--mount",
            f"type=bind,source={vm_dir.resolve()},target=/vm",
            "--mount",
            f"type=bind,source={workspace.resolve()},target=/workspace",
        ]
        if spec.network.outbound == "deny":
            args += ["--network", "none"]
        else:
            # Allow outbound traffic. Allowlist support can be implemented via custom networks.
            pass
        args += [spec.image, "sleep", "infinity"]
        self._run_docker(tuple(args))
        self._run_docker(("start", container_name))

    def _start_agent(self, container_name: str) -> None:
        self._run_docker(
            (
                "exec",
                "-d",
                container_name,
                "python3",
                "/workspace/.vm_agent/agent_server.py",
            )
        )

    def _wait_for_agent(self, agent_dir: Path, timeout: float = 20.0) -> None:
        status_file = agent_dir / "status.json"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if status_file.exists():
                try:
                    payload = json.loads(status_file.read_text())
                    if payload.get("state") == "ready":
                        return
                except Exception:
                    pass
            time.sleep(0.1)
        raise RuntimeError("VM agent did not become ready in time")

    def _run_docker(self, args: tuple[str, ...], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a docker command composed from trusted arguments."""
        suspicious_chars = {";", "&", "|", "$", ">", "<", "`"}
        for arg in args:
            if not isinstance(arg, str):
                raise ValueError(f"docker arguments must be str, got {type(arg)}: {arg!r}")
            if any(char in arg for char in suspicious_chars):
                raise ValueError(f"suspicious shell metacharacter detected in docker argument: {arg!r}")
        cmd = ["docker", *args]
        return subprocess.run(cmd, check=check, capture_output=False, text=True)

    def _vm_dir(self, vm_id: str) -> Path:
        return self.root / vm_id

    def _metadata_path(self, vm_dir: Path) -> Path:
        return vm_dir / "metadata.json"

    def _write_metadata(self, vm_dir: Path, vm: VirtualMachine) -> None:
        payload = self._serialize_vm(vm)
        metadata_path = self._metadata_path(vm_dir)
        metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _read_metadata(self, vm_dir: Path) -> VirtualMachine:
        metadata_path = self._metadata_path(vm_dir)
        if not metadata_path.exists():
            raise VmNotFoundError(f"Metadata is missing for VM at {vm_dir}")
        payload = json.loads(metadata_path.read_text())
        return self._deserialize_vm(payload, vm_dir)

    def _serialize_vm(self, vm: VirtualMachine) -> Dict[str, Any]:
        spec_dict = asdict(vm.spec)
        spec_dict["network"]["allowlist"] = list(spec_dict["network"]["allowlist"])
        return {
            "vm_id": vm.id,
            "session_id": vm.session_id,
            "state": vm.state.value,
            "spec": spec_dict,
            "workspace_path": str(vm.workspace_path),
            "created_at": vm.created_at.isoformat(),
            "updated_at": vm.updated_at.isoformat(),
            "backend": vm.backend,
            "backend_data": vm.backend_data,
        }

    def _deserialize_vm(self, payload: Dict[str, Any], vm_dir: Path) -> VirtualMachine:
        spec_payload = payload["spec"]
        resources = VmResources(**spec_payload["resources"])
        network_payload = spec_payload["network"]
        network = VmNetworkPolicy(
            outbound=network_payload["outbound"],
            allowlist=tuple(network_payload.get("allowlist", ())),
        )
        spec = VmSpec(
            image=spec_payload["image"],
            resources=resources,
            network=network,
            ttl_sec=spec_payload["ttl_sec"],
        )
        workspace_path = Path(payload.get("workspace_path") or (vm_dir / "workspace"))
        backend_data = payload.get("backend_data") or {}
        return VirtualMachine(
            id=payload["vm_id"],
            session_id=payload["session_id"],
            spec=spec,
            state=VirtualMachineState(payload["state"]),
            workspace_path=workspace_path,
            created_at=datetime.fromisoformat(payload["created_at"]),
            updated_at=datetime.fromisoformat(payload["updated_at"]),
            backend=payload.get("backend", "docker"),
            backend_data=backend_data,
        )

    def _read_container_name(self, vm_dir: Path) -> str | None:
        metadata_path = self._metadata_path(vm_dir)
        if not metadata_path.exists():
            return None
        payload = json.loads(metadata_path.read_text())
        backend_data = payload.get("backend_data") or {}
        return backend_data.get("container")


def _resolve_now(value: datetime | None = None) -> datetime:
    resolved = value or timezone.now()
    if timezone.is_naive(resolved):
        resolved = timezone.make_aware(resolved, timezone.get_current_timezone())
    return resolved


__all__ = ["VmBackend", "LocalVmBackend", "DockerVmBackend"]
