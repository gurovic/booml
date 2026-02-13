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
    Импортирует ноутбук из .ipynb файла.
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
    
    try:
        file_content = uploaded_file.read().decode('utf-8')
        notebook_data = json.loads(file_content)
        
        # Проверяем, является ли это валидным .ipynb по содержимому
        if 'cells' not in notebook_data:
            return JsonResponse({
                'status': 'error',
                'message': 'Неверный формат файла. Ожидается структура .ipynb с ключом "cells"'
            }, status=400)
        
        cells_data = notebook_data.get('cells', [])
        
        # Определяем название ноутбука
        notebook_title = 'Импортированный блокнот'
        
        # Пытаемся получить название из метаданных Booml
        booml_metadata = notebook_data.get('metadata', {}).get('booml_metadata', {})
        if booml_metadata.get('booml_title'):
            notebook_title = booml_metadata['booml_title']
        elif 'metadata' in notebook_data and 'name' in notebook_data['metadata']:
            notebook_title = notebook_data['metadata']['name']
        
        # Определяем устройство вычислений
        raw_device = booml_metadata.get('compute_device', '').strip().lower()
        if raw_device not in (Notebook.ComputeDevice.CPU, Notebook.ComputeDevice.GPU):
            raw_device = Notebook.ComputeDevice.CPU
        
        # Проверяем на дубликаты
        if Notebook.objects.filter(owner=user, title=notebook_title).exists():
            counter = 1
            while Notebook.objects.filter(owner=user, title=f"{notebook_title} ({counter})").exists():
                counter += 1
            notebook_title = f"{notebook_title} ({counter})"
        
        # Создаем новый ноутбук
        notebook = Notebook.objects.create(
            owner=user,
            title=notebook_title,
            compute_device=raw_device
        )
        
        # Создаем ячейки
        created_cells = []
        errors = []
        execution_order = 0
        
        for idx, cell_data in enumerate(cells_data):
            try:
                source_cell_type = cell_data.get('cell_type', 'code')
                source = cell_data.get('source', [])
                
                # Конвертируем источник в строку
                if isinstance(source, list):
                    content = '\n'.join(source)
                else:
                    content = str(source)
                
                # Определяем тип ячейки для Booml
                if source_cell_type == 'code':
                    cell_type = Cell.CODE
                    # Пытаемся извлечь вывод из ячейки
                    outputs = cell_data.get('outputs', [])
                    output_content = ''
                    
                    for output in outputs:
                        output_type = output.get('output_type', '')
                        if output_type == 'stream':
                            text = output.get('text', '')
                            if isinstance(text, list):
                                text = ''.join(text)
                            output_content += text
                        elif output_type == 'execute_result' or output_type == 'display_data':
                            data = output.get('data', {})
                            # Пытаемся найти текстовое представление
                            if 'text/plain' in data:
                                output_content += str(data['text/plain'])
                            elif 'text/html' in data:
                                output_content += str(data['text/html'])
                        elif output_type == 'error':
                            ename = output.get('ename', 'Error')
                            evalue = output.get('evalue', '')
                            output_content += f"Ошибка: {ename} - {evalue}"
                    
                    # Сохраняем вывод как JSON для совместимости
                    if output_content:
                        output_json = json.dumps({
                            'stdout': output_content,
                            'error': False
                        }, ensure_ascii=False)
                    else:
                        output_json = ''
                
                elif source_cell_type == 'markdown':
                    # Проверяем, была ли это исходно LaTeX ячейка
                    metadata = cell_data.get('metadata', {})
                    if metadata.get('original_type') == 'latex':
                        cell_type = Cell.LATEX
                        # Убираем $$ обертку, если она есть
                        content_cleaned = content.strip()
                        if content_cleaned.startswith('$$') and content_cleaned.endswith('$$'):
                            content = content_cleaned[2:-2].strip()
                    else:
                        cell_type = Cell.TEXT
                    output_json = ''
                
                else:
                    # Неизвестный тип - используем код по умолчанию
                    cell_type = Cell.CODE
                    output_json = ''
                
                # Создаем ячейку
                cell = Cell.objects.create(
                    notebook=notebook,
                    cell_type=cell_type,
                    content=content,
                    output=output_json,
                    execution_order=execution_order
                )
                created_cells.append(cell.id)
                execution_order += 1
                
            except Exception as e:
                errors.append(f"Ячейка {idx + 1}: ошибка создания - {str(e)}")
        
        response_data = {
            'status': 'success',
            'message': f'Ноутбук успешно импортирован. Создано ячеек: {len(created_cells)}',
            'notebook_id': notebook.id
        }
        if errors:
            response_data['errors'] = errors
        return JsonResponse(response_data)

    except json.JSONDecodeError as e:
        # Файл должен быть валидным JSON (.ipynb)
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка парсинга JSON: {str(e)}. Убедитесь, что файл является валидным .ipynb'
        }, status=400)
    except UnicodeDecodeError as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка декодирования файла: {str(e)}. Файл должен быть в кодировке UTF-8'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка импорта: {str(e)}'
        }, status=400)
