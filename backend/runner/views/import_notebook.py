import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

from ..models import Notebook, Cell


@csrf_exempt
@require_http_methods(["POST"])
def import_notebook(request):
    """
    Импортирует ноутбук из JSON файла.
    Создает новый ноутбук на основе импортированных данных.
    """
    User = get_user_model()
    

    user = request.user if request.user.is_authenticated else None
    

    if 'file' not in request.FILES:
        return JsonResponse({
            'status': 'error',
            'message': 'Файл не был загружен'
        }, status=400)
    
    uploaded_file = request.FILES['file']
    

    if not uploaded_file.name.endswith('.json'):
        return JsonResponse({
            'status': 'error',
            'message': 'Поддерживаются только JSON файлы'
        }, status=400)
    
    try:

        file_content = uploaded_file.read().decode('utf-8')
        notebook_data = json.loads(file_content)
        

        if 'notebook' not in notebook_data or 'cells' not in notebook_data:
            return JsonResponse({
                'status': 'error',
                'message': 'Неверный формат файла. Ожидается структура с полями "notebook" и "cells"'
            }, status=400)
        
        notebook_info = notebook_data['notebook']
        cells_data = notebook_data.get('cells', [])
        

        notebook_title = notebook_info.get('title', 'Импортированный блокнот')

        if Notebook.objects.filter(owner=user, title=notebook_title).exists():
            counter = 1
            while Notebook.objects.filter(owner=user, title=f"{notebook_title} ({counter})").exists():
                counter += 1
            notebook_title = f"{notebook_title} ({counter})"
        
        notebook = Notebook.objects.create(
            owner=user,
            title=notebook_title
        )
        

        created_cells = []
        errors = []
        
        for idx, cell_data in enumerate(cells_data):
            try:
                cell_type = cell_data.get('cell_type', Cell.CODE)

                if cell_type not in [choice[0] for choice in Cell.TYPE_CHOICES]:
                    errors.append(f"Ячейка {idx + 1}: неверный тип '{cell_type}', используется 'code'")
                    cell_type = Cell.CODE
                
                cell = Cell.objects.create(
                    notebook=notebook,
                    cell_type=cell_type,
                    content=cell_data.get('content', ''),
                    output=cell_data.get('output', ''),
                    execution_order=cell_data.get('execution_order', idx)
                )
                created_cells.append(cell.id)
            except Exception as e:
                errors.append(f"Ячейка {idx + 1}: ошибка создания - {str(e)}")
        

        response_data = {
            'status': 'success',
            'message': f'Ноутбук успешно импортирован. Создано ячеек: {len(created_cells)}',
            'notebook_id': notebook.id,
            'notebook_title': notebook.title,
            'cells_created': len(created_cells),
            'cells_total': len(cells_data),
        }
        
        if errors:
            response_data['warnings'] = errors
            response_data['message'] += f'. Предупреждений: {len(errors)}'
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка парсинга JSON: {str(e)}'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка импорта: {str(e)}'
        }, status=500)

