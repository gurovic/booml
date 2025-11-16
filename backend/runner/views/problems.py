# python
from django.shortcuts import render
from django.core.paginator import Paginator
from ..models import Problem

def problem_list(request):
    problems = Problem.objects.only("title", "created_at", "rating").order_by("-created_at")

    min_r = request.GET.get("min_rating")
    max_r = request.GET.get("max_rating")
    try:
        if min_r is not None and min_r != "":
            problems = problems.filter(rating__gte=int(min_r))
        if max_r is not None and max_r != "":
            problems = problems.filter(rating__lte=int(max_r))
    except (ValueError, TypeError):
        # некорректные значения — игнорируем фильтр
        pass

    paginator = Paginator(problems, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop("page", None)
    querystring = params.urlencode()

    return render(request, "runner/problem_list.html", {
        "page_obj": page_obj,
        "querystring": querystring,
        "min_rating": min_r or "",
        "max_rating": max_r or "",
    })
