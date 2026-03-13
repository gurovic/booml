from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from ..services.permissions import get_user_writable_notebook_or_404


@require_http_methods(["POST", "DELETE"])
def delete_notebook(request, notebook_id):
    notebook = get_user_writable_notebook_or_404(request.user, notebook_id)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        result = {"status": "success", "notebook_id": notebook.id}
        notebook.delete()
        return JsonResponse(result)

    notebook.delete()
    messages.success(request, "Блокнот удалён")
    return redirect("runner:notebook_list")
