from django.shortcuts import render, get_object_or_404
from mainsite.models import Submission


def submission_history(request):
    """Хронологический список посылок пользователя"""
    submissions = Submission.objects.filter(user=request.user).order_by("-submitted_at")
    return render(request, "submissions/history.html", {"submissions": submissions})


def submission_detail(request, pk):
    """Просмотр конкретной посылки"""
    submission = get_object_or_404(Submission, pk=pk, user=request.user)
    return render(request, "submissions/detail.html", {"submission": submission})


def submission_compare(request, pk1, pk2):
    """Сравнение двух посылок по метрикам"""
    sub1 = get_object_or_404(Submission, pk=pk1, user=request.user)
    sub2 = get_object_or_404(Submission, pk=pk2, user=request.user)

    metrics = []
    if sub1.metrics and sub2.metrics:
        for key in set(sub1.metrics.keys()) | set(sub2.metrics.keys()):
            metrics.append({
                "name": key,
                "val1": sub1.metrics.get(key),
                "val2": sub2.metrics.get(key),
            })

    return render(
        request,
        "submissions/compare.html",
        {"sub1": sub1, "sub2": sub2, "metrics": metrics},
    )
