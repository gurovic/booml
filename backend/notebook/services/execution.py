from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest

from notebook.runner.notebook.executor import cfg, run_python


def _build_media_url(request: HttpRequest, relative_path: str) -> str:
    media_url = settings.MEDIA_URL or "/"
    if not media_url.endswith("/"):
        media_url += "/"
    clean_relative = relative_path.lstrip("/")
    return request.build_absolute_uri(f"{media_url}{clean_relative}")


def execute_cell_code(cell, code: str, request: HttpRequest) -> Dict[str, Any]:
    """Run the provided code, persist the result on the cell and return the payload."""
    media_root = Path(settings.MEDIA_ROOT)
    media_root.mkdir(parents=True, exist_ok=True)

    result = run_python(code, media_root)
    result_dict: Dict[str, Any] = asdict(result)
    run_id = result_dict.get("run_id", "")

    for output in result_dict.get("outputs", []):
        data: Dict[str, Any] = output.get("data", {})
        name = data.get("name")
        if not name:
            continue
        relative = f"{cfg.RUNS_SUBDIR}/{run_id}/{name}"
        if output.get("type") == "image":
            data["url"] = _build_media_url(request, relative)
        elif output.get("type") == "table":
            data["download_url"] = _build_media_url(request, relative)
        elif output.get("type") == "html":
            data["source_url"] = _build_media_url(request, relative)

    cell.content = code
    cell.output = json.dumps(result_dict, ensure_ascii=False)
    cell.save(update_fields=["content", "output"])

    return result_dict
