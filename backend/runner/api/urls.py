from django.urls import path
from .views import SubmissionCreateView, MySubmissionsListView

urlpatterns = [
    path("submissions/", SubmissionCreateView.as_view(), name="submission-create"),
    path("submissions/mine/", MySubmissionsListView.as_view(), name="submission-list-mine"),
]
