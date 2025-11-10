from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from ..models import NotebookCell


@csrf_exempt
@require_POST
def duplicate_cell(request, notebook_id, cell_id):
    """Дублирование ячейки (как в Jupyter/Colab)."""
    cell = get_object_or_404(NotebookCell, notebook_id=notebook_id, id=cell_id)
    clone = NotebookCell.objects.create(
        notebook=cell.notebook,
        cell_type=cell.cell_type,
        content=cell.content,
        output=cell.output,
        execution_order=cell.execution_order + 1,
    )
    return JsonResponse({"status": "ok", "cell": {"id": clone.id}})
