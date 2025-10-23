from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models import Notebook


@require_http_methods(["POST"])
def create_notebook(request):
    try:
        notebook = Notebook.objects.create(
            title="Новый блокнот",
            owner=request.user,
            # problem=None
        )
        return JsonResponse({
            'status': 'success',
            'notebook_id': notebook.id
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)