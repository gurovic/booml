# python
from django.shortcuts import render
from django.core.paginator import Paginator
from ..models import Problem

def problem_list_polygon(request):
    Problems = Problem.objects.filter(author=request.user.id).order_by("id").only('title','rating','is_published')
    paginator = Paginator(Problems, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "runner/polygon/problem_list.html", {
        "page_obj": page_obj,
        "querystring": querystring,
    })
