from django.shortcuts import render
from ..models import Notebook
from django.contrib.auth.decorators import login_required

@login_required
def notebook_list(request):
    notebooks = Notebook.objects.filter(owner=request.user).order_by("id")
    return render(request, 'notebook/notebook_list.html', {
        'notebooks': notebooks
    })