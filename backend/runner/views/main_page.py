from django.shortcuts import render
from ..models import Problem

def main_page(request):
    problems = Problem.objects.only("title", "statement", "created_at","rating").order_by("?")[:15]
    return render(request, "runner/main_page.html", {"problems": problems})
