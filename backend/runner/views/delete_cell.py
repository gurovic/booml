from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models import Notebook, Cell


@require_http_methods(["DELETE"])
def delete_cell(request, notebook_id, cell_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    cell = get_object_or_404(Cell, id=cell_id, notebook=notebook)
    cell.delete()
    return JsonResponse({'status': 'success'})