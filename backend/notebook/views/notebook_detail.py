from django.shortcuts import render, get_object_or_404
from notebook.models import Notebook


def notebook_detail(request, notebook_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    cells = notebook.cells.all()
    return render(request, 'notebook_detail.html', {
        'notebook': notebook,
        'cells': cells
    })