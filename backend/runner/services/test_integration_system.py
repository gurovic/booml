from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from . import enqueue_submission_for_evaluation
from .prevalidation_service import run_prevalidation
from ..views.problem_detail import _report_is_valid
from ..models import Submission, Problem, ProblemDescriptor

@override_settings(
  CELERY_TASK_ALWAYS_EAGER=True,
  CELERY_TASK_EAGER_PROPAGATES=True
)
class IntegrationPrevalidationTest(TestCase):
  def setUp(self):
    self.user = get_user_model().objects.create(username="tester")
    self.problem = Problem.objects.create(title="Test problem")
    ProblemDescriptor.objects.create(problem=self.problem)

  def test_valid_flow(self):
    content = "id,prediction\n1,0.9\n2,0.3\n"

    uploaded_file = SimpleUploadedFile(
      "submission.csv",
      content.encode("utf-8"),
      content_type="text/csv"
    )

    submission = Submission.objects.create(
      user=self.user,
      problem=self.problem,
      file=uploaded_file,
      status=Submission.STATUS_PENDING
    )

    report = run_prevalidation(submission)
    self.assertTrue(_report_is_valid(report))

    enqueue_submission_for_evaluation.delay(submission.id)
    self.assertIn(submission.status, [Submission.STATUS_PENDING, Submission.STATUS_RUNNING, Submission.STATUS_VALIDATED])

  def test_invalid_flow(self):
    content = "id,prediction\nx,0.9\n2,abc\n"

    uploaded_file = SimpleUploadedFile(
      "submission.csv",
      content.encode("utf-8"),
      content_type="text/csv"
    )

    submission = Submission.objects.create(
      user=self.user,
      problem=self.problem,
      file=uploaded_file,
      status=Submission.STATUS_PENDING
    )

    report = run_prevalidation(submission)
    self.assertFalse(_report_is_valid(report))
