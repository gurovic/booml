import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from ..models import Notebook, Cell


@csrf_exempt
@require_http_methods(["GET", "POST"])
def export_notebook(request, notebook_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    
    # Собираем ячейки в формате .ipynb
    cells_data = []
    execution_count = 1
    
    for cell in notebook.cells.all().order_by('execution_order'):
        if cell.cell_type == Cell.CODE:
            # Ячейка кода
            outputs = []
            if cell.output:
                # Пытаемся распарсить вывод как JSON (если это вывод ячейки выполнения)
                try:
                    output_data = json.loads(cell.output)
                    if isinstance(output_data, dict):
                        if output_data.get('error'):
                            outputs.append({
                                'output_type': 'error',
                                'ename': 'Error',
                                'evalue': output_data.get('error', ''),
                                'traceback': []
                            })
                        else:
                            # Обычный вывод
                            if output_data.get('stdout'):
                                outputs.append({
                                    'output_type': 'stream',
                                    'name': 'stdout',
                                    'text': output_data['stdout']
                                })
                            if output_data.get('outputs'):
                                for output_item in output_data['outputs']:
                                    outputs.append({
                                        'output_type': 'execute_result',
                                        'data': output_item,
                                        'execution_count': execution_count,
                                        'metadata': {}
                                    })
                except (json.JSONDecodeError, AttributeError):
                    # Если не удалось распарсить, сохраняем как plain text
                    outputs.append({
                        'output_type': 'stream',
                        'name': 'stdout',
                        'text': cell.output
                    })
            
            cells_data.append({
                'cell_type': 'code',
                'execution_count': execution_count,
                'metadata': {},
                'outputs': outputs,
                'source': cell.content.split('\n') if cell.content else []
            })
            execution_count += 1
            
        elif cell.cell_type == Cell.TEXT:
            # Markdown ячейка
            cells_data.append({
                'cell_type': 'markdown',
                'metadata': {},
                'source': cell.content.split('\n') if cell.content else []
            })
            
        elif cell.cell_type == Cell.LATEX:
            # LaTeX ячейка - конвертируем в markdown с математическими вставками
            latex_content = cell.content or ''
            # Оборачиваем LaTeX в $$ для отображения в .ipynb
            markdown_content = f"$$\n{latex_content}\n$$"
            cells_data.append({
                'cell_type': 'markdown',
                'metadata': {
                    'original_type': 'latex'  # Сохраняем информацию о типе
                },
                'source': markdown_content.split('\n')
            })
    
    # Формируем структуру .ipynb
    notebook_data = {
        'cells': cells_data,
        'metadata': {
            'kernelspec': {
                'display_name': 'Python 3',
                'language': 'python',
                'name': 'python3'
            },
            'language_info': {
                'name': 'python',
                'version': '3.8.0'
            },
            'booml_metadata': {  # Сохраняем метаданные Booml
                'booml_notebook_id': notebook.id,
                'booml_title': notebook.title,
                'compute_device': notebook.compute_device,
                'created_at': notebook.created_at.isoformat() if notebook.created_at else None,
                'updated_at': notebook.updated_at.isoformat() if notebook.updated_at else None,
            }
        },
        'nbformat': 4,
        'nbformat_minor': 5
    }
    
    json_content = json.dumps(notebook_data, ensure_ascii=False, indent=2)
    
    if request.method == 'GET':
        # Используем правильный MIME type для .ipynb файлов
        response = HttpResponse(json_content, content_type='application/x-ipynb+json; charset=utf-8')
        # Очищаем имя файла от недопустимых символов
        safe_title = "".join(c for c in notebook.title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        filename = f"{safe_title}_{notebook.id}.ipynb"
        # Явно указываем расширение .ipynb в Content-Disposition
        response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{filename}'
        return response
    
    return JsonResponse({
        'status': 'success',
        'data': notebook_data,
        'filename': f"{notebook.title.replace(' ', '_')}_{notebook.id}.ipynb"
    })
