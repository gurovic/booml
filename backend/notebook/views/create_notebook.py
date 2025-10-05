from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from notebook.models import Notebook


@require_http_methods(["POST"])
def create_notebook(request):
    notebook = Notebook.objects.create(title="Новый блокнот")
    return JsonResponse({
        'status': 'success',
        'notebook_id': notebook.id
    })