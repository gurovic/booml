from django.shortcuts import render, get_object_or_404
from ..models import Task, Submission


def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    submissions = Submission.objects.filter(task=task).order_by('-created_at')

    # Логика для определения результата
    result = None
    if submissions.exists():
        best_submission = submissions.filter(metric__isnull=False).order_by('-metric').first()
        if best_submission and best_submission.metric >= task.passing_score:
            result = {"status": "OK", "metric": best_submission.metric}
        else:
            result = {"status": "FAILED"}

    context = {
        'task': task,
        'submissions': submissions,
        'result': result,
    }
    return render(request, 'runner/task_detail.html', context)