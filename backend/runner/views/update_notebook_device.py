import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..models import Notebook
from ..services.permissions import get_user_notebook_or_404


def _parse_json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


@require_http_methods(["PATCH", "POST"])
def update_notebook_device(request, notebook_id):
    notebook = get_user_notebook_or_404(request.user, notebook_id)
    payload = _parse_json_body(request)
    raw_device = (payload.get("compute_device") or "").strip().lower()
    if raw_device not in (Notebook.ComputeDevice.CPU, Notebook.ComputeDevice.GPU):
        return JsonResponse(
            {
                "status": "error",
                "message": "Недопустимое устройство вычислений",
            },
            status=400,
        )

    notebook.compute_device = raw_device
    notebook.save(update_fields=["compute_device"])

    return JsonResponse(
        {
            "status": "success",
            "notebook_id": notebook.id,
            "compute_device": notebook.compute_device,
        }
    )
