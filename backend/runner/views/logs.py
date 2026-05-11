import csv
import io
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from runner.services.user_access import is_platform_admin

# Maximum number of lines/rows to return per log type
_MAX_APP_LOG_LINES = 500
_MAX_ERROR_ROWS = 200


def _read_app_log(path: Path, max_lines: int = _MAX_APP_LOG_LINES) -> list[dict]:
    """Read the last *max_lines* lines from the plain-text app log."""
    entries = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return entries
    lines = text.splitlines()
    for line in lines[-max_lines:]:
        line = line.strip()
        if not line:
            continue
        # Each line has format: "<timestamp> <LEVEL> <logger> <message…>"
        parts = line.split(" ", 3)
        if len(parts) >= 4:
            entries.append(
                {
                    "timestamp": f"{parts[0]} {parts[1]}",
                    "level": parts[2],
                    "logger": parts[3].split(" ", 1)[0] if " " in parts[3] else parts[3],
                    "message": parts[3].split(" ", 1)[1] if " " in parts[3] else "",
                    "source": "app.log",
                }
            )
        else:
            entries.append(
                {
                    "timestamp": "",
                    "level": "",
                    "logger": "",
                    "message": line,
                    "source": "app.log",
                }
            )
    return entries


def _read_errors_csv(path: Path, max_rows: int = _MAX_ERROR_ROWS) -> list[dict]:
    """Read the last *max_rows* data rows from the CSV error log."""
    entries = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return entries
    reader = csv.DictReader(io.StringIO(text))
    all_rows = list(reader)
    for row in all_rows[-max_rows:]:
        entries.append(
            {
                "timestamp": row.get("timestamp", ""),
                "level": row.get("level", ""),
                "logger": row.get("logger", ""),
                "module": row.get("module", ""),
                "pathname": row.get("pathname", ""),
                "lineno": row.get("lineno", ""),
                "message": row.get("message", ""),
                "exception": row.get("exception", ""),
                "source": "errors.csv",
            }
        )
    return entries


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def logs_api(request):
    """
    Return recent log entries from app.log and errors.csv.
    Restricted to platform administrators.
    """
    if not is_platform_admin(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    app_log_path: Path = getattr(settings, "APP_LOG_PATH", None)
    error_csv_path: Path = getattr(settings, "ERROR_CSV_LOG_PATH", None)

    app_entries = _read_app_log(app_log_path) if app_log_path else []
    error_entries = _read_errors_csv(error_csv_path) if error_csv_path else []

    return JsonResponse(
        {
            "app_log": app_entries,
            "error_log": error_entries,
        }
    )
