import json

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from ..models import Cell
from ..services.permissions import get_user_writable_notebook_or_404


def _parse_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body or '{}')
        except (TypeError, ValueError):
            return {}
    return request.POST


def _validate_target_position(raw_value, max_index):
    try:
        position = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError('Некорректная позиция')

    if position < 0 or position > max_index:
        raise ValueError('Позиция вне диапазона')

    return position


def _reindex_cells(cells):
    for index, cell in enumerate(cells):
        if cell.execution_order != index:
            Cell.objects.filter(pk=cell.pk).update(execution_order=index)
            cell.execution_order = index


@transaction.atomic
@require_http_methods(["PATCH", "POST"])
def move_cell(request, notebook_id, cell_id):
    notebook = get_user_writable_notebook_or_404(request.user, notebook_id)
    payload = _parse_payload(request)

    target_position = payload.get('target_position')
    if target_position is None:
        return JsonResponse({'status': 'error', 'message': 'Не указана целевая позиция'}, status=400)

    cells = list(notebook.cells.select_for_update().order_by('execution_order'))

    try:
        target_index = _validate_target_position(target_position, len(cells) - 1)
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)

    cell = next((item for item in cells if item.id == cell_id), None)
    if cell is None:
        return JsonResponse({'status': 'error', 'message': 'Ячейка не найдена'}, status=404)

    current_index = cells.index(cell)
    if current_index != target_index:
        cells.pop(current_index)
        cells.insert(target_index, cell)
        _reindex_cells(cells)

    order = [{'id': c.id, 'execution_order': c.execution_order} for c in cells]
    return JsonResponse({'status': 'success', 'order': order})


@transaction.atomic
@require_http_methods(["POST"])
def copy_cell(request, notebook_id, cell_id):
    notebook = get_user_writable_notebook_or_404(request.user, notebook_id)
    payload = _parse_payload(request)

    cells = list(notebook.cells.select_for_update().order_by('execution_order'))
    source = next((item for item in cells if item.id == cell_id), None)
    if source is None:
        return JsonResponse({'status': 'error', 'message': 'Ячейка не найдена'}, status=404)

    default_position = cells.index(source) + 1
    max_allowed = len(cells)

    target_value = payload.get('target_position', default_position)
    try:
        target_index = _validate_target_position(target_value, max_allowed)
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)

    new_cell = Cell.objects.create(
        notebook=notebook,
        cell_type=source.cell_type,
        content=source.content,
        output='',
        execution_order=target_index,
    )

    cells.insert(target_index, new_cell)
    _reindex_cells(cells)

    html = render_to_string('notebook/cell.html', {'cell': new_cell, 'notebook': notebook})

    return JsonResponse({
        'status': 'success',
        'cell_id': new_cell.id,
        'execution_order': new_cell.execution_order,
        'html': html,
    })
