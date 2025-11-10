from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List

from django.utils import timezone

DEFAULT_SESSION_TTL_SECONDS = 3600


@dataclass
class RuntimeSession:
    namespace: str
    created_at: datetime
    updated_at: datetime


_sessions: Dict[str, RuntimeSession] = {}


def _resolve_now(value: datetime | None = None) -> datetime:
    resolved = value or timezone.now()
    if timezone.is_naive(resolved):
        resolved = timezone.make_aware(resolved, timezone.get_current_timezone())
    return resolved


def create_session(namespace: str, *, now: datetime | None = None) -> RuntimeSession:
    current = _resolve_now(now)
    session = RuntimeSession(namespace=namespace, created_at=current, updated_at=current)
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


__all__ = [
    "RuntimeSession",
    "DEFAULT_SESSION_TTL_SECONDS",
    "create_session",
    "get_session",
    "reset_session",
    "cleanup_expired",
]
