from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
import shutil

from django.conf import settings


@dataclass(frozen=True)
class VmConfig:
    backend: str
    image: str
    cpu: int
    ram_mb: int
    disk_gb: int
    ttl_sec: int
    net_outbound: str
    net_allowlist: Tuple[str, ...]
    root_dir: Path


def get_vm_config() -> VmConfig:
    backend_name = _resolve_backend(getattr(settings, "RUNTIME_VM_BACKEND", "auto"))
    image_name = getattr(settings, "RUNTIME_VM_IMAGE", "runner-vm:latest")
    cpu = int(getattr(settings, "RUNTIME_VM_CPU", 2))
    ram_mb = int(getattr(settings, "RUNTIME_VM_RAM_MB", 4096))
    disk_gb = int(getattr(settings, "RUNTIME_VM_DISK_GB", 32))
    ttl_sec = int(getattr(settings, "RUNTIME_VM_TTL_SEC", 3600))
    net_outbound = str(getattr(settings, "RUNTIME_VM_NET_OUTBOUND", "deny"))
    allowlist = _normalize_allowlist(getattr(settings, "RUNTIME_VM_NET_ALLOWLIST", ()))
    root_value = getattr(settings, "RUNTIME_VM_ROOT", None) or (Path(settings.BASE_DIR) / "media" / "notebook_sessions")
    root_path = _resolve_root(root_value)
    root_path.mkdir(parents=True, exist_ok=True)

    return VmConfig(
        backend=backend_name,
        image=image_name,
        cpu=cpu,
        ram_mb=ram_mb,
        disk_gb=disk_gb,
        ttl_sec=ttl_sec,
        net_outbound=net_outbound,
        net_allowlist=allowlist,
        root_dir=root_path,
    )


def _resolve_root(path_value: Path | str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = (settings.BASE_DIR / path).resolve()
    return path


def _normalize_allowlist(raw: object) -> Tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return tuple(item.strip() for item in raw.split(",") if item.strip())
    if isinstance(raw, (list, tuple)):
        normalized = []
        for item in raw:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized.append(text)
        return tuple(normalized)
    return ()


def _resolve_backend(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in ("", "auto"):
        return "docker" if shutil.which("docker") else "local"
    return normalized


__all__ = ["VmConfig", "get_vm_config"]
