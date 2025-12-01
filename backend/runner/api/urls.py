from django.urls import path
from .views import (
    CourseCreateView,
    CourseParticipantsUpdateView,
    SubmissionCreateView,
    MySubmissionsListView,
    CreateNotebookSessionView,
    ResetSessionView,
    RunCellView,
    SessionFilesView,
    SessionFileDownloadView,
    StopSessionView,
)

urlpatterns = [
    path("submissions/", SubmissionCreateView.as_view(), name="submission-create"),
    path("submissions/mine/", MySubmissionsListView.as_view(), name="submission-list-mine"),
    path("sessions/notebook/", CreateNotebookSessionView.as_view(), name="notebook-session-create"),
    path("sessions/reset/", ResetSessionView.as_view(), name="session-reset"),
    path("sessions/stop/", StopSessionView.as_view(), name="session-stop"),
    path("sessions/files/", SessionFilesView.as_view(), name="session-files"),
    path("sessions/file/", SessionFileDownloadView.as_view(), name="session-file-download"),
    path("cells/run/", RunCellView.as_view(), name="run-cell"),
    path("courses/", CourseCreateView.as_view(), name="course-create"),
    path(
        "courses/<int:course_id>/participants/",
        CourseParticipantsUpdateView.as_view(),
        name="course-participants-update",
    ),
]
