from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Tuple


class VirtualMachineState(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass(frozen=True)
class VmResources:
    cpu: int
    ram_mb: int
    disk_gb: int


@dataclass(frozen=True)
class VmNetworkPolicy:
    outbound: str
    allowlist: Tuple[str, ...]


@dataclass(frozen=True)
class VmSpec:
    image: str
    resources: VmResources
    network: VmNetworkPolicy
    ttl_sec: int


@dataclass
class VirtualMachine:
    id: str
    session_id: str
    spec: VmSpec
    state: VirtualMachineState
    workspace_path: Path
    created_at: datetime
    updated_at: datetime
    backend: str = "local"
    backend_data: Dict[str, str] = field(default_factory=dict)


__all__ = [
    "VirtualMachineState",
    "VmResources",
    "VmNetworkPolicy",
    "VmSpec",
    "VirtualMachine",
]
