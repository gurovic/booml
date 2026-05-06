from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from ..models import Cell
from ..services.permissions import get_user_writable_notebook_or_404


@require_http_methods(["POST"])
def create_text_cell(request, notebook_id):
    notebook = get_user_writable_notebook_or_404(request.user, notebook_id)

    last_cell = notebook.cells.order_by('-execution_order').first()
    new_order = last_cell.execution_order + 1 if last_cell else 0
    
    cell = Cell.objects.create(
        notebook=notebook,
        cell_type=Cell.TEXT,
        content='',
        execution_order=new_order,
    )

    if request.content_type and 'application/json' in request.content_type:
        return JsonResponse({
            'status': 'success',
            'cell': {
                'id': cell.id,
                'cell_type': cell.cell_type,
                'content': cell.content,
                'output': cell.output,
                'execution_order': cell.execution_order,
            },
        })

    return render(request, 'notebook/cell.html', {'cell': cell, 'notebook': notebook})
