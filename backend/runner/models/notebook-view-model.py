import uuid
import time
import io
import contextlib
import traceback
import json
import subprocess

from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, HttpResponseBadRequest
from .models import CodeRun

@csrf_protect
def code_runner_template(request):
    if request.method == 'GET':
        return render(request, 'code_runner.html')
    elif request.method == 'POST':
        code = request.POST.get('code', '')
        lang = request.POST.get('lang', 'python')
        run_id = str(uuid.uuid4())
        result = run_code_and_save(code, lang, run_id)
        return render(request, 'code_runner.html', {'result': result, 'code': code})
    else:
        return HttpResponseBadRequest("Method not allowed")

@csrf_protect
def code_run_api(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'errors': [{'code': 'bad_method', 'msg': 'POST only'}]}, status=405)
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        lang = data.get('lang', 'python')
        run_id = data.get('run_id') or str(uuid.uuid4())
        result = run_code_and_save(code, lang, run_id)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'ok': False, 'errors': [{'code': 'server_error', 'msg': str(e)}]}, status=500)

def run_code_and_save(code, lang, run_id):
    start_time = time.time()
    result_text = ""
    error_text = ""
    errors = []
    stats = {'exit_code': 0, 'timeout': False}
    try:
        # Важно: замените на безопасную песочницу! Здесь под капотом subprocess с изоляцией.
        proc = subprocess.run(
            ['python3', '-c', code],
            capture_output=True,
            text=True,
            timeout=5  # ограничиваем время выполнения
        )
        result_text = proc.stdout
        error_text = proc.stderr
        stats['exit_code'] = proc.returncode
    except subprocess.TimeoutExpired:
        error_text = "Timeout during execution"
        stats['exit_code'] = 2  # специальный код
        stats['timeout'] = True
        errors.append({'code': 'timeout', 'msg': error_text})
    except Exception:
        error_text = traceback.format_exc()
        stats['exit_code'] = 1
        errors.append({'code': 'runtime_error', 'msg': 'Exception during execution'})

    elapsed = int((time.time() - start_time) * 1000)
    # Сохраняем результат в базу
    CodeRun.objects.create(
        run_id=run_id,
        code=code,
        lang=lang,
        result=result_text,
        stderr=error_text,
        elapsed_ms=elapsed,
        exit_code=stats['exit_code']
    )
    return {
        'ok': len(errors) == 0,
        'run_id': run_id,
        'elapsed_ms': elapsed,
        'outputs': [{'type': 'text', 'data': {'text': result_text}}] if result_text.strip() else [],
        'stderr': error_text,
        'stats': stats,
        'errors': errors
    }
