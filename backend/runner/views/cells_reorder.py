from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from ..models import NotebookCell


@csrf_exempt
@require_POST
def reorder_cells(request, notebook_id):
    """
    Меняет порядок ячеек — принимает JSON с порядком ID:
    { "order": [3, 1, 2, 4] }
    """
    try:
        import json
        body = json.loads(request.body.decode("utf-8"))
        order = body.get("order", [])
        if not isinstance(order, list):
            raise ValueError
    except Exception:
        return HttpResponseBadRequest("Некорректный формат данных")

    for idx, cell_id in enumerate(order):
        NotebookCell.objects.filter(notebook_id=notebook_id, id=cell_id).update(
            execution_order=idx
        )

    return JsonResponse({"status": "ok"})
