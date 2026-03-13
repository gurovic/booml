from django.http import JsonResponse

from ..models import Course, Problem, Contest


def search(request):

    q = request.GET.get("q", "")
    search_type = request.GET.get("type", "all")

    courses = []
    problems = []
    contests = []

    if q:
        if search_type in ["all", "course"]:
            courses = list(
                Course.objects.filter(title__icontains=q)
                .values("id", "title")
            )

        if search_type in ["all", "problem"]:
            problems = list(
                Problem.objects.filter(title__icontains=q)
                .values("id", "title", "rating")
            )

        if search_type in ["all", "contest"]:
            contests = list(
                Contest.objects.filter(title__icontains=q)
                .values("id", "title")
            )

    return JsonResponse({
        "courses": courses,
        "problems": problems,
        "contests": contests
    })
