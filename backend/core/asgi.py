"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DOCKER_DIR = BACKEND_DIR / "docker"
if str(DOCKER_DIR) not in sys.path:
    sys.path.insert(0, str(DOCKER_DIR))

from vm_bootstrap import ensure_vm_environment

ensure_vm_environment()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402
from runner.services.runtime import register_runtime_shutdown_hooks  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
register_runtime_shutdown_hooks()

django_asgi_app = get_asgi_application()

from runner import routing as runner_routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(runner_routing.websocket_urlpatterns)
        ),
    }
)
