import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from notebook.models import Notebook, Cell
from notebook.services.execution import execute_cell_code


@require_http_methods(["POST"])
def execute_cell(request, notebook_id, cell_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    cell = get_object_or_404(Cell, id=cell_id, notebook=notebook)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    code = payload.get("code", cell.content)

    result = execute_cell_code(cell, code, request)
    return JsonResponse(result)
