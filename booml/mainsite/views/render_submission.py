import json
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, JsonResponse
from mainsite.models import SubmissionModel

@require_http_methods(["POST"])
@csrf_exempt
def render_submission(request: HttpRequest):
    """
    POST: принимает JSON от тестирующей системы, создаёт SubmissionModel и
    рендерит display.html. Ничего не сохраняет.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"error": f"Bad JSON: {e}"}, status=400)

    submission = SubmissionModel.from_raw(data)
    context = {
        "submission": submission,
        "raw_pretty": json.dumps(submission.raw, ensure_ascii=False, indent=2),
    }
    return render(request, "mainsite/display.html", context)
