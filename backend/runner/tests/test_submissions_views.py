from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from ..models.task import Task
from ..views.submissions import submission_list


class SubmissionListViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.task = Task.objects.create(title='Test Task', description='desc', metric_name='Accuracy')

    @patch("runner.views.submissions.Submission")
    def test_submission_list_returns_ok_status(self, mock_submission):
        mock_qs = MagicMock()
        mock_submission.objects.filter.return_value = mock_qs
        mock_qs.exists.return_value = True
        mock_qs.order_by.return_value = mock_qs

        request = self.factory.get(f"/task/{self.task.id}/submissions/")
        request.user = self.user

        response = submission_list(request, self.task.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn("runner/submissions/list.html", response.template_name)
        self.assertIn("task", response.context_data)
        self.assertIn("submissions", response.context_data)

    @patch("runner.views.submissions.Submission")
    def test_submission_list_no_submissions(self, mock_submission):
        mock_qs = MagicMock()
        mock_submission.objects.filter.return_value = mock_qs
        mock_qs.exists.return_value = False

        request = self.factory.get(f"/task/{self.task.id}/submissions/")
        request.user = self.user

        response = submission_list(request, self.task.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn("task", response.context_data)
        self.assertFalse(response.context_data["submissions"].exists())
