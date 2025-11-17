import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from ..models import Notebook, Cell


@require_http_methods(["POST"])
def save_text_cell(request, notebook_id, cell_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    cell = get_object_or_404(Cell, id=cell_id, notebook=notebook)
    
    try:
        # Получаем данные из JSON body
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body or '{}')
            content = data.get('content', '')
        else:
            content = request.POST.get('content', '')
        
        # Сохраняем содержимое ячейки
        cell.content = content
        cell.save()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)