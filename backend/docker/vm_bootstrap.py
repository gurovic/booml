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
    docker_available = _docker_available()

    if requested in ("docker", "auto") and docker_available:
        os.environ["RUNTIME_VM_BACKEND"] = "docker"
        # Clean up old session containers on startup
        _cleanup_old_sessions()
        image = os.environ.setdefault("RUNTIME_VM_IMAGE", DEFAULT_IMAGE)
        if not _docker_image_exists(image):
            dockerfile = _resolve_dockerfile()
            if dockerfile:
                print(
                    f"[vm-bootstrap] Docker image '{image}' не найден. "
                    f"Попытка сборки образа...",
                    file=sys.stderr,
                )
                try:
                    _build_docker_image(image, dockerfile)
                    print(
                        f"[vm-bootstrap] Образ '{image}' успешно собран!",
                        file=sys.stderr,
                    )
                    return
                except Exception as exc:
                    print(
                        f"[vm-bootstrap] Не удалось собрать образ: {exc}",
                        file=sys.stderr,
                    )
                    hint = "python docker/docker_build.py"
                    hint += f" --dockerfile {dockerfile}"
                    print(
                        f"[vm-bootstrap] Попробуйте вручную: `{hint}`",
                        file=sys.stderr,
                    )
            if requested == "auto":
                os.environ["RUNTIME_VM_BACKEND"] = "local"
            return
        return

    if requested == "docker" and not docker_available:
        print(
            "WARNING: RUNTIME_VM_BACKEND=docker, но docker daemon недоступен — "
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


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return False


def _resolve_dockerfile() -> Path | None:
    override = os.environ.get("RUNTIME_VM_DOCKERFILE")
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        else:
            path = path.resolve()
        if path.exists():
            return path
    return DEFAULT_DOCKERFILE if DEFAULT_DOCKERFILE.exists() else None


def _build_docker_image(image: str, dockerfile: Path) -> None:
    """
    Build Docker image from Dockerfile.
    Uses docker_build.py if available, otherwise runs docker build directly.
    """
    docker_build_script = BACKEND_DIR / "docker" / "docker_build.py"
    context = BACKEND_DIR if dockerfile.parent == BACKEND_DIR / "docker" else dockerfile.parent
    
    if docker_build_script.exists():
        # Use docker_build.py script
        result = subprocess.run(
            [sys.executable, str(docker_build_script), "--dockerfile", str(dockerfile)],
            cwd=str(BACKEND_DIR),
        )
    else:
        # Fallback: use docker build directly
        result = subprocess.run(
            ["docker", "build", "-t", image, "-f", str(dockerfile), str(context)],
            cwd=str(BACKEND_DIR),
        )
    
    if result.returncode != 0:
        raise RuntimeError(f"Docker build failed with return code {result.returncode}")


def _cleanup_old_sessions() -> None:
    """
    Remove old session containers (runner-*) on startup.
    This ensures no orphaned containers remain from previous runs.
    """
    try:
        # Get all containers with name pattern runner-*
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=^runner-", "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode == 0 and result.stdout.strip():
            container_ids = result.stdout.strip().split("\n")
            if container_ids:
                print(
                    f"[vm-bootstrap] Удаление {len(container_ids)} старых сессий...",
                    file=sys.stderr,
                )
                # Remove all old session containers
                subprocess.run(
                    ["docker", "rm", "-f"] + container_ids,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                )
    except Exception as exc:
        print(
            f"[vm-bootstrap] Предупреждение: не удалось очистить старые сессии: {exc}",
            file=sys.stderr,
        )


__all__ = ["ensure_vm_environment", "get_vm_settings"]
