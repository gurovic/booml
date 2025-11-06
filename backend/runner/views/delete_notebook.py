from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from ..models import Notebook


@require_http_methods(["POST", "DELETE"])
def delete_notebook(request, notebook_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        result = {"status": "success", "notebook_id": notebook.id}
        notebook.delete()
        return JsonResponse(result)

    notebook.delete()
    messages.success(request, "Блокнот удалён")
    return redirect("runner:notebook_list")
