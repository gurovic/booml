import json

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods

from ..models import Notebook, Cell


def _wants_json_response(request):
    return bool(request.content_type and 'application/json' in request.content_type)


def _serialize_cell(cell):
    return {
        'id': cell.id,
        'cell_type': cell.cell_type,
        'content': cell.content,
        'output': cell.output,
        'execution_order': cell.execution_order,
    }


def _resolve_cell_type(request):
    cell_type = Cell.CODE

    if request.content_type and 'application/json' in request.content_type:
        try:
            payload = json.loads(request.body or '{}')
        except (TypeError, ValueError):
            payload = {}
        else:
            cell_type = payload.get('type', cell_type)
    else:
        cell_type = request.POST.get('type', cell_type)

    allowed_types = {choice[0] for choice in Cell.TYPE_CHOICES}
    if cell_type not in allowed_types:
        return Cell.CODE

    return cell_type


def _create_cell(notebook, cell_type):
    last_cell = notebook.cells.order_by('-execution_order').first()
    new_order = last_cell.execution_order + 1 if last_cell else 0

    default_content = 'print("Hello World")' if cell_type == Cell.CODE else ''

    return Cell.objects.create(
        notebook=notebook,
        cell_type=cell_type,
        content=default_content,
        execution_order=new_order,
    )


@require_http_methods(["POST"])
def create_cell(request, notebook_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    cell_type = _resolve_cell_type(request)
    cell = _create_cell(notebook, cell_type)

    if _wants_json_response(request):
        return JsonResponse({'status': 'success', 'cell': _serialize_cell(cell)})

    return render(request, 'notebook/cell.html', {'cell': cell, 'notebook': notebook})


@require_http_methods(["POST"])
def create_latex_cell(request, notebook_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    cell = _create_cell(notebook, Cell.LATEX)

    if _wants_json_response(request):
        return JsonResponse({'status': 'success', 'cell': _serialize_cell(cell)})

    return render(request, 'notebook/cell.html', {'cell': cell, 'notebook': notebook})
