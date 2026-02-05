from django.shortcuts import render
from django.http import JsonResponse
from ..services.permissions import get_user_notebook_or_404


def notebook_detail(request, notebook_id):
    notebook = get_user_notebook_or_404(request.user, notebook_id)
    cells = notebook.cells.all()
    return render(request, 'notebook/notebook_detail.html', {
        'notebook': notebook,
        'cells': cells
    })


def notebook_detail_api(request, notebook_id):
    notebook = get_user_notebook_or_404(request.user, notebook_id)
    cells = notebook.cells.all()

    return JsonResponse({
        "id": notebook.id,
        "title": notebook.title,
        "compute_device": notebook.compute_device,
        "owner_id": notebook.owner_id,
        "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
        "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None,
        "cells": [
            {
                "id": cell.id,
                "cell_type": cell.cell_type,
                "content": cell.content,
                "output": cell.output,
                "execution_order": cell.execution_order,
            }
            for cell in cells
        ],
    })
