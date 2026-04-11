from __future__ import annotations

from typing import Any

import requests
from django.conf import settings


class CaptchaError(Exception):
    """Base error for captcha verification failures."""


class CaptchaValidationError(CaptchaError):
    """Raised when the visitor did not solve captcha successfully."""


class CaptchaConfigError(CaptchaError):
    """Raised when captcha is enabled but misconfigured."""


def is_captcha_enabled() -> bool:
    return settings.CAPTCHA_PROVIDER == "turnstile"


def get_captcha_site_key() -> str:
    if not is_captcha_enabled():
        return ""
    return settings.TURNSTILE_SITE_KEY


def get_client_ip(request) -> str:
    if request is None:
        return ""

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return (request.META.get("REMOTE_ADDR") or "").strip()


def verify_turnstile_token(token: str, *, remote_ip: str = "") -> dict[str, Any]:
    if not settings.TURNSTILE_SECRET_KEY:
        raise CaptchaConfigError("Turnstile secret key is not configured.")

    if not token:
        raise CaptchaValidationError("Подтвердите, что вы не робот.")

    payload = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = requests.post(
            settings.TURNSTILE_VERIFY_URL,
            data=payload,
            timeout=5,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CaptchaValidationError(
            "Не удалось проверить капчу. Попробуйте ещё раз."
        ) from exc

    if result.get("success"):
        return result

    raise CaptchaValidationError("Проверка капчи не пройдена. Попробуйте ещё раз.")
