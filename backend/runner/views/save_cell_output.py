from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from ..models import Notebook, Cell


@csrf_exempt
@require_http_methods(["POST"])
def save_cell_output(request, notebook_id, cell_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    cell = get_object_or_404(Cell, id=cell_id, notebook=notebook)

    data = json.loads(request.body)
    cell.content = data.get('code', '')
    cell.output = data.get('output', '')
    cell.save()

    return JsonResponse({'status': 'success'})