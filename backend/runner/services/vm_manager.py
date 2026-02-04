from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from typing import Mapping

from .vm_backends import DockerVmBackend, LocalVmBackend, VmBackend
from .vm_config import VmConfig, get_vm_config
from .vm_exceptions import VmNotFoundError
from .vm_models import (
    VirtualMachine,
    VmNetworkPolicy,
    VmResources,
    VmSpec,
)

SAFE_ID_PATTERN = re.compile(r"[^A-Za-z0-9_.-]")
_vm_manager: VmManager | None = None


def sanitize_session_id(session_id: str) -> str:
    return SAFE_ID_PATTERN.sub("_", session_id)


class VmManager:
    """High-level helper that turns runtime sessions into VM instances."""

    def __init__(self, *, config: VmConfig, backend: VmBackend):
        self.config = config
        self.backend = backend

    def ensure_session_vm(
        self,
        session_id: str,
        *,
        overrides: Mapping[str, object] | None = None,
        now: datetime | None = None,
    ) -> VirtualMachine:
        vm_id = self._build_vm_id(session_id)
        try:
            return self.backend.get_vm(vm_id)
        except VmNotFoundError:
            spec = self.build_default_spec()
            if overrides:
                spec = self._apply_overrides(spec, overrides)
            return self.backend.create_vm(vm_id=vm_id, session_id=session_id, spec=spec, now=now)

    def destroy_session_vm(self, session_id: str) -> None:
        vm_id = self._build_vm_id(session_id)
        try:
            self.backend.delete_vm(vm_id)
        except VmNotFoundError:
            return

    def build_default_spec(self) -> VmSpec:
        return VmSpec(
            image=self.config.image,
            resources=VmResources(
                cpu=self.config.cpu,
                ram_mb=self.config.ram_mb,
                disk_gb=self.config.disk_gb,
            ),
            network=VmNetworkPolicy(
                outbound=self.config.net_outbound,
                allowlist=self.config.net_allowlist,
            ),
            ttl_sec=self.config.ttl_sec,
            gpu=False,
        )

    def _apply_overrides(self, spec: VmSpec, overrides: Mapping[str, object]) -> VmSpec:
        updated = spec
        if "image" in overrides and overrides["image"]:
            updated = replace(updated, image=str(overrides["image"]))

        resource_fields = {
            key: overrides[key]
            for key in ("cpu", "ram_mb", "disk_gb")
            if key in overrides and overrides[key] is not None
        }
        if resource_fields:
            updated = replace(
                updated,
                resources=VmResources(
                    cpu=int(resource_fields.get("cpu", updated.resources.cpu)),
                    ram_mb=int(resource_fields.get("ram_mb", updated.resources.ram_mb)),
                    disk_gb=int(resource_fields.get("disk_gb", updated.resources.disk_gb)),
                ),
            )

        if "ttl_sec" in overrides and overrides["ttl_sec"] is not None:
            updated = replace(updated, ttl_sec=int(overrides["ttl_sec"]))

        if "gpu" in overrides:
            updated = replace(updated, gpu=bool(overrides["gpu"]))

        network_fields = {
            key: overrides[key]
            for key in ("net_outbound", "net_allowlist")
            if key in overrides
        }
        if network_fields:
            outbound = str(network_fields.get("net_outbound", updated.network.outbound))
            allowlist = network_fields.get("net_allowlist", updated.network.allowlist)
            allowlist_tuple = _normalize_allowlist(allowlist)
            updated = replace(
                updated,
                network=VmNetworkPolicy(outbound=outbound, allowlist=allowlist_tuple),
            )

        return updated

    def _build_vm_id(self, session_id: str) -> str:
        safe_session_id = sanitize_session_id(session_id or "")
        if not safe_session_id:
            raise ValueError("session_id must contain at least one safe character")
        return f"runner-{safe_session_id}"


def get_vm_manager() -> VmManager:
    global _vm_manager
    if _vm_manager is None:
        config = get_vm_config()
        backend = _build_backend(config)
        _vm_manager = VmManager(config=config, backend=backend)
    return _vm_manager


def reset_vm_manager() -> None:
    global _vm_manager
    _vm_manager = None


def _build_backend(config: VmConfig) -> VmBackend:
    backend_name = (config.backend or "").strip().lower()
    if backend_name in ("local", "", None):
        return LocalVmBackend(config.root_dir)
    if backend_name == "docker":
        return DockerVmBackend(config.root_dir)
    raise ValueError(f"Unsupported VM backend: {config.backend!r}")


def _normalize_allowlist(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, (list, tuple)):
        normalized = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized.append(text)
        return tuple(normalized)
    return ()


__all__ = ["VmManager", "get_vm_manager", "reset_vm_manager", "sanitize_session_id"]
