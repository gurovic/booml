from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from django.conf import settings
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from .executor import run_python, OutputItem, RUNS_SUBDIR

MEDIA_ROOT = Path(getattr(settings, "MEDIA_ROOT"))

def _bad(msg: str, code: str = "bad_request", status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "errors": [{"code": code, "msg": msg}]},
                        status=status, json_dumps_params={"ensure_ascii": False})

@csrf_protect
@require_POST
def run_view(req: HttpRequest):
    try:
        body = json.loads(req.body.decode("utf-8"))
    except Exception:
        return _bad("invalid json")

    code = body.get("code")
    lang = (body.get("lang") or "").lower()
    rid  = body.get("run_id")

    if not isinstance(code, str) or not code.strip():
        return _bad("field 'code' is required and must be non-empty string")
    if lang not in {"python", "py", ""}:
        return _bad("only 'python' is supported for now", code="unsupported_lang")

    res = run_python(code=code, media_root=MEDIA_ROOT, run_id=rid)

    def ser(o: OutputItem) -> Dict[str, Any]:
        d = {"type": o.type, "data": dict(o.data)}
        # Для image/table добавляем прямой URL к файлу (dev/просто):
        if o.type in {"image", "table"} and "name" in o.data:
            d["data"]["url"] = f"/media/{RUNS_SUBDIR}/{res.run_id}/{o.data['name']}"
        return d

    payload: Dict[str, Any] = {
        "ok": res.ok,
        "run_id": res.run_id,
        "elapsed_ms": res.stats.elapsed_ms,
        "outputs": [ser(o) for o in res.outputs],
        "stderr": res.stderr,
        "stats": {
            "exit_code": res.stats.exit_code,
            "cpu_s": res.stats.cpu_s,
            "mem_mb": res.stats.mem_mb,
            "timeout": res.stats.timeout,
        },
        "errors": res.errors,
    }
    return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})