#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from vm_bootstrap import get_vm_settings  # noqa: E402

CONFIG = get_vm_settings()
DEFAULT_IMAGE = os.environ.get("RUNTIME_VM_IMAGE", CONFIG.get("image", "runner-vm:latest"))
_config_dockerfile = CONFIG.get("dockerfile") or (BACKEND_DIR / "docker" / "Dockerfile")
DEFAULT_DOCKERFILE = Path(os.environ.get("RUNTIME_VM_DOCKERFILE", _config_dockerfile)).expanduser().resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build (or rebuild) the runner VM docker image.")
    parser.add_argument(
        "--image",
        default=DEFAULT_IMAGE,
        help=f"Имя docker-образа (по умолчанию {DEFAULT_IMAGE}).",
    )
    parser.add_argument(
        "--dockerfile",
        default=str(DEFAULT_DOCKERFILE),
        help="Путь к Dockerfile (по умолчанию backend/docker/Dockerfile).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Не использовать кэш при сборке образа.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dockerfile = Path(args.dockerfile).expanduser().resolve()
    if not dockerfile.exists():
        print(f"ERROR: Dockerfile {dockerfile} не найден.", file=sys.stderr)
        return 1
    context = dockerfile.parent
    cmd = ["docker", "build", "-t", args.image, "-f", str(dockerfile)]
    if args.no_cache:
        cmd.append("--no-cache")
    cmd.append(str(context))
    print(f"[docker-build] Building {args.image} from {dockerfile}")
    if args.no_cache:
        print("[docker-build] Building without cache...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[docker-build] docker build failed (exit code {exc.returncode})", file=sys.stderr)
        return exc.returncode
    print(f"[docker-build] Image {args.image} built successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
