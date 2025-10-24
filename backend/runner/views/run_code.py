import json
import os
from pathlib import Path
from urllib.parse import urljoin

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from ..services import executor


@csrf_protect
@require_http_methods(["POST"])
def run_code(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        lang = data.get('lang', 'python')
        run_id = data.get('run_id')

        if not code.strip():
            return JsonResponse({
                'status': 'error',
                'message': 'Code cannot be empty'
            }, status=400)

        if lang != 'python':
            return JsonResponse({
                'status': 'error',
                'message': 'Only Python language is supported'
            }, status=400)

        media_root = Path(settings.MEDIA_ROOT).resolve()

        result = executor.run_python(
            code=code,
            media_root=media_root,
            run_id=run_id
        )

        artifacts_payload = serialize_artifacts(result.artifacts, media_root, request)

        response_data = {
            'status': 'success' if result.ok else 'error',
            'run_id': result.run_id,
            'output': format_output(result),
            'stats': {
                'execution_time_ms': result.stats.elapsed_ms,
                'memory_used_mb': result.stats.mem_mb,
                'timeout': result.stats.timeout,
                'exit_code': result.stats.exit_code
            },
            'errors': result.errors,
            'artifacts': artifacts_payload
        }

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Execution error: {str(e)}'
        }, status=500)


def serialize_artifacts(artifacts, media_root: Path, request) -> list[dict]:
    media_root = media_root.resolve()
    media_url = settings.MEDIA_URL or '/'
    base_media_url = request.build_absolute_uri(media_url)
    if not base_media_url.endswith('/'):
        base_media_url = f"{base_media_url}/"
    serialized = []

    for artifact_path in artifacts:
        try:
            relative_path = artifact_path.resolve().relative_to(media_root)
            relative_url = "/".join(relative_path.parts)
        except Exception:
            relative_path = Path(artifact_path.name)
            relative_url = relative_path.name

        artifact_name = relative_path.name
        relative_url_normalized = relative_url.replace(os.sep, '/')
        absolute_url = urljoin(base_media_url, relative_url_normalized)
        serialized.append({
            'name': artifact_name,
            'url': absolute_url
        })

    return serialized


def format_output(result):
    output_parts = []

    for item in result.outputs:
        if item.type == 'text' and item.data.get('text'):
            output_parts.append(item.data['text'])

    if result.stderr:
        output_parts.append(f"STDERR:\n{result.stderr}")

    if result.errors:
        error_messages = [f"{error['code']}: {error['msg']}" for error in result.errors]
        output_parts.append(f"ERRORS:\n" + "\n".join(error_messages))

    return "\n".join(output_parts) if output_parts else "No output"
