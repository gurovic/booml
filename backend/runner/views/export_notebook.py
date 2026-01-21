import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from ..models import Notebook


@csrf_exempt
@require_http_methods(["GET", "POST"])
def export_notebook(request, notebook_id):

    notebook = get_object_or_404(Notebook, id=notebook_id)
    
  
    cells_data = []
    for cell in notebook.cells.all().order_by('execution_order'):
        cells_data.append({
            'cell_type': cell.cell_type,
            'content': cell.content,
            'output': cell.output,
            'execution_order': cell.execution_order,
        })
    
    notebook_data = {
        'version': '1.0',
        'notebook': {
            'title': notebook.title,
            'compute_device': notebook.compute_device,
            'created_at': notebook.created_at.isoformat() if notebook.created_at else None,
            'updated_at': notebook.updated_at.isoformat() if notebook.updated_at else None,
        },
        'cells': cells_data,
    }
    
    json_content = json.dumps(notebook_data, ensure_ascii=False, indent=2)
    

    if request.method == 'GET':
        response = HttpResponse(json_content, content_type='application/json; charset=utf-8')
        filename = f"{notebook.title.replace(' ', '_')}_{notebook.id}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    

    return JsonResponse({
        'status': 'success',
        'data': notebook_data,
        'filename': f"{notebook.title.replace(' ', '_')}_{notebook.id}.json"
    })

