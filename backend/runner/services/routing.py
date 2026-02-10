from __future__ import annotations

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/submissions/(?P<submission_id>\d+)/$",
        consumers.SubmissionMetricConsumer.as_asgi(),
    ),
    re_path(
        r"^ws/problems/(?P<problem_id>\d+)/submissions/$",
        consumers.ProblemSubmissionsConsumer.as_asgi(),
    ),
]
