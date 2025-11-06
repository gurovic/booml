from datetime import date

from django.test import Client, TestCase
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User

from runner.models.problem import Problem


class SubmissionListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.problem = Problem.objects.create(
            title='Test Problem',
            statement='desc',
            rating=1200,
            created_at=date.today(),
        )
        self.client.force_login(self.user)

    @patch("runner.views.submissions.Submission")
    def test_submission_list_returns_ok_status(self, mock_submission):
        mock_qs = MagicMock()
        mock_submission.objects.filter.return_value = mock_qs
        mock_qs.exists.return_value = True
        mock_qs.order_by.return_value = mock_qs

        response = self.client.get(f"/problem/{self.problem.id}/submissions/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "runner/submissions/list.html")
        self.assertIn("problem", response.context)
        self.assertIn("submissions", response.context)

    @patch("runner.views.submissions.Submission")
    def test_submission_list_no_submissions(self, mock_submission):
        mock_qs = MagicMock()
        mock_submission.objects.filter.return_value = mock_qs
        mock_qs.exists.return_value = False
        mock_qs.order_by.return_value = mock_qs

        response = self.client.get(f"/problem/{self.problem.id}/submissions/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("problem", response.context)
        self.assertEqual(response.context["submissions"], [])
