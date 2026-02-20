from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models import Cell
from ..services.permissions import get_user_writable_notebook_or_404


@require_http_methods(["DELETE"])
def delete_cell(request, notebook_id, cell_id):
    notebook = get_user_writable_notebook_or_404(request.user, notebook_id)
    cell = get_object_or_404(Cell, id=cell_id, notebook=notebook)
    cell.delete()
    return JsonResponse({'status': 'success'})
