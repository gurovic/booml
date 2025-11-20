from django.http import Http404
from ..models import Notebook

def get_user_notebook_or_404(user, notebook_id):
    try:
        nb = Notebook.objects.get(id=notebook_id)
    except Notebook.DoesNotExist:
        raise Http404("Notebook not found")

    if nb.owner != user:
        raise Http404("Notebook not found")

    return nb