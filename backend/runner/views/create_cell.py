from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from ..models import Notebook, Cell


@require_http_methods(["POST"])
def create_cell(request, notebook_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)

    last_cell = notebook.cells.order_by('-execution_order').first()
    new_order = last_cell.execution_order + 1 if last_cell else 0

    cell = Cell.objects.create(
        notebook=notebook,
        content='print("Hello World")',
        execution_order=new_order
    )

    return render(request, 'cell.html', {'cell': cell})