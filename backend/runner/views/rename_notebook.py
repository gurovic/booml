import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from ..models import Notebook


def _parse_json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


@require_http_methods(["POST", "PATCH"])
def rename_notebook(request, notebook_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    content_type = request.headers.get("Content-Type", "")
    is_json_request = "application/json" in content_type

    if is_json_request:
        payload = _parse_json_body(request)
        new_title = (payload.get("title") or "").strip()

        if not new_title:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Название блокнота не может быть пустым",
                },
                status=400,
            )

        notebook.title = new_title
        notebook.save(update_fields=["title"])

        return JsonResponse(
            {
                "status": "success",
                "notebook_id": notebook.id,
                "title": notebook.title,
            }
        )

    # HTML form submission
    new_title = (request.POST.get("title") or "").strip()

    if not new_title:
        messages.error(request, "Название блокнота не может быть пустым")
        return redirect("runner:notebook_detail", notebook_id=notebook.id)

    notebook.title = new_title
    notebook.save(update_fields=["title"])
    messages.success(request, "Название блокнота обновлено")

    return redirect("runner:notebook_detail", notebook_id=notebook.id)
