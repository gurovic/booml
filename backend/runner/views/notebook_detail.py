from django.shortcuts import render
from ..services.permissions import get_user_notebook_or_404


def notebook_detail(request, notebook_id):
    notebook = get_user_notebook_or_404(request.user, notebook_id)
    cells = notebook.cells.all()
    return render(request, 'notebook/notebook_detail.html', {
        'notebook': notebook,
        'cells': cells
    })
