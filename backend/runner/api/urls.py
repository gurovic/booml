from django.urls import path
from .views import (
    SubmissionCreateView,
    MySubmissionsListView,
    CreateNotebookSessionView,
    ResetSessionView,
)

urlpatterns = [
    path("submissions/", SubmissionCreateView.as_view(), name="submission-create"),
    path("submissions/mine/", MySubmissionsListView.as_view(), name="submission-list-mine"),
    path("sessions/notebook/", CreateNotebookSessionView.as_view(), name="notebook-session-create"),
    path("sessions/reset/", ResetSessionView.as_view(), name="session-reset"),
]
