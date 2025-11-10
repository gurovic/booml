from __future__ import annotations

import io
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List

from django.utils import timezone

DEFAULT_SESSION_TTL_SECONDS = 3600


@dataclass
class RuntimeSession:
    namespace: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class RuntimeExecutionResult:
    stdout: str
    stderr: str
    error: str | None
    variables: Dict[str, str]


_sessions: Dict[str, RuntimeSession] = {}


def _resolve_now(value: datetime | None = None) -> datetime:
    resolved = value or timezone.now()
    if timezone.is_naive(resolved):
        resolved = timezone.make_aware(resolved, timezone.get_current_timezone())
    return resolved


def _new_namespace() -> Dict[str, Any]:
    # each session gets its own globals dict preloaded with safe builtins
    return {"__builtins__": __builtins__}


def create_session(namespace: str, *, now: datetime | None = None) -> RuntimeSession:
    current = _resolve_now(now)
    session = RuntimeSession(namespace=_new_namespace(), created_at=current, updated_at=current)
    _sessions[namespace] = session
    return session


def get_session(namespace: str, *, touch: bool = True, now: datetime | None = None) -> RuntimeSession | None:
    session = _sessions.get(namespace)
    if session and touch:
        session.updated_at = _resolve_now(now)
    return session


def reset_session(namespace: str, *, now: datetime | None = None) -> RuntimeSession:
    _sessions.pop(namespace, None)
    return create_session(namespace, now=now)


def cleanup_expired(
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    *,
    now: datetime | None = None,
) -> List[str]:
    if ttl_seconds <= 0:
        ttl_seconds = 0
    current = _resolve_now(now)
    cutoff = current - timedelta(seconds=ttl_seconds)
    expired: List[str] = []
    for namespace, session in list(_sessions.items()):
        if session.updated_at < cutoff:
            expired.append(namespace)
            _sessions.pop(namespace, None)
    return expired


def _get_or_create_session(session_id: str) -> RuntimeSession:
    session = get_session(session_id, touch=False)
    if session is None:
        session = create_session(session_id)
    return session


def _snapshot_variables(namespace: Dict[str, Any]) -> Dict[str, str]:
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


def run_code(session_id: str, code: str) -> RuntimeExecutionResult:
    session = _get_or_create_session(session_id)
    namespace = session.namespace

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    error: str | None = None

    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        try:
            exec(code, namespace, namespace)
        except Exception:
            error = traceback.format_exc()

    session.updated_at = _resolve_now()

    return RuntimeExecutionResult(
        stdout=stdout_buffer.getvalue(),
        stderr=stderr_buffer.getvalue(),
        error=error,
        variables=_snapshot_variables(namespace),
    )


__all__ = [
    "RuntimeSession",
    "RuntimeExecutionResult",
    "DEFAULT_SESSION_TTL_SECONDS",
    "create_session",
    "get_session",
    "reset_session",
    "cleanup_expired",
    "run_code",
]
