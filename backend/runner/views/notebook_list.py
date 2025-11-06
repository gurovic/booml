from django.shortcuts import render
from ..models import Notebook


def notebook_list(request):
    notebooks = Notebook.objects.all()
    return render(request, 'notebook/notebook_list.html', {
        'notebooks': notebooks
    })