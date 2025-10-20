from django.shortcuts import render
from ...runner.models import Notebook


def notebook_list(request):
    notebooks = Notebook.objects.all()
    return render(request, 'notebook_list.html', {
        'notebooks': notebooks
    })