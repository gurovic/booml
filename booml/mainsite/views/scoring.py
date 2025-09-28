from django.http import HttpResponse, HttpRequest, JsonResponse
import json

from mainsite import models

# Create your views here.
def score_submission(req: HttpRequest):
    # TODO: add scoring system
    # models.Score.objects.create()
    # and creating objects
    # now i wouldn't like to add objects into db because it's just a trash
    return JsonResponse({
        "status": "accepted",
        "time": 1000,
        "memory": 256,
        "metrics": [
            1.0, # accuracy
            1.0  # F1-score
        ],
        "errors": []
    })
