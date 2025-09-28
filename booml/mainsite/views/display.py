import json
from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest
from mainsite.models import Submission

def display_submission(request: HttpRequest, pk: int):
    submission = get_object_or_404(Submission, pk=pk)

    raw_pretty = None
    if hasattr(submission, "raw") and submission.raw:
        raw_pretty = json.dumps(submission.raw, ensure_ascii=False, indent=2)

    context = {
        "submission": submission,
        "raw_pretty": raw_pretty,
    }
    return render(request, "mainsite/display.html", context)
