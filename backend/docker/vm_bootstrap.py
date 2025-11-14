from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = "runner-vm:latest"
DEFAULT_DOCKERFILE = BACKEND_DIR / "docker" / "Dockerfile"
DEFAULT_CONFIG_PATH = Path(__file__).with_name("vm_settings.json")

_CONFIG_CACHE: Dict[str, Any] | None = None

CONFIG_ENV_MAP = {
    "backend": "RUNTIME_VM_BACKEND",
    "image": "RUNTIME_VM_IMAGE",
    "root": "RUNTIME_VM_ROOT",
    "cpu": "RUNTIME_VM_CPU",
    "ram_mb": "RUNTIME_VM_RAM_MB",
    "disk_gb": "RUNTIME_VM_DISK_GB",
    "ttl_sec": "RUNTIME_VM_TTL_SEC",
    "net_outbound": "RUNTIME_VM_NET_OUTBOUND",
    "net_allowlist": "RUNTIME_VM_NET_ALLOWLIST",
    "dockerfile": "RUNTIME_VM_DOCKERFILE",
}


def ensure_vm_environment() -> None:
    """
    Prepare environment variables so the runtime backend can pick Docker automatically.
    """
    config = get_vm_settings()
    _apply_config_defaults(config)

    requested = os.environ.get("RUNTIME_VM_BACKEND", "auto").strip().lower()
    docker_available = shutil.which("docker") is not None

    if requested in ("docker", "auto") and docker_available:
        os.environ["RUNTIME_VM_BACKEND"] = "docker"
        image = os.environ.setdefault("RUNTIME_VM_IMAGE", DEFAULT_IMAGE)
        if not _docker_image_exists(image):
            dockerfile = _resolve_dockerfile()
            hint = "python docker/docker_build.py"
            if dockerfile:
                hint += f" --dockerfile {dockerfile}"
            print(
                f"[vm-bootstrap] Docker image '{image}' не найден. "
                f"Выполните `{hint}` чтобы его собрать.",
                file=sys.stderr,
            )
        return

    if requested == "docker" and not docker_available:
        print(
            "WARNING: RUNTIME_VM_BACKEND=docker, но docker CLI не найден — "
            "переключаюсь на локальный runtime.",
            file=sys.stderr,
        )
    os.environ.setdefault("RUNTIME_VM_BACKEND", "local")


def get_vm_settings() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return dict(_CONFIG_CACHE)
    path = Path(os.environ.get("RUNTIME_VM_CONFIG", DEFAULT_CONFIG_PATH))
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except Exception as exc:  # pragma: no cover
            print(f"[vm-bootstrap] Не удалось прочитать {path}: {exc}", file=sys.stderr)
            data = {}
    else:
        data = {}
    _CONFIG_CACHE = data
    return dict(data)


def _apply_config_defaults(config: Dict[str, Any]) -> None:
    for key, env_var in CONFIG_ENV_MAP.items():
        if env_var in os.environ:
            continue
        if key not in config:
            continue
        value = config[key]
        if key in {"root", "dockerfile"}:
            value = _resolve_path(value)
        elif key == "net_allowlist" and isinstance(value, (list, tuple)):
            value = ",".join(str(item) for item in value)
        os.environ[env_var] = str(value)


def _resolve_path(value: str | os.PathLike[str]) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    return str(path)


def _docker_image_exists(image: str) -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _resolve_dockerfile() -> Path | None:
    override = os.environ.get("RUNTIME_VM_DOCKERFILE")
    if override:
        path = Path(override).expanduser().resolve()
        return path if path.exists() else None
    return DEFAULT_DOCKERFILE if DEFAULT_DOCKERFILE.exists() else None


__all__ = ["ensure_vm_environment", "get_vm_settings"]
