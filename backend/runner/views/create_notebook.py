from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models import Notebook


@require_http_methods(["POST"])
def create_notebook(request):
    try:
        owner = request.user if request.user.is_authenticated else None
        notebook = Notebook.objects.create(
            title="Новый блокнот",
            owner=owner,
            # problem=None
        )
        return JsonResponse({
            'status': 'success',
            'notebook_id': notebook.id,
            'title': notebook.title,
            'owner': notebook.owner.username if notebook.owner else None,
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)