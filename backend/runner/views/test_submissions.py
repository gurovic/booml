from datetime import date

from django.test import Client, TestCase
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

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
        mock_qs.__iter__.return_value = []

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
        mock_qs.__iter__.return_value = []

        response = self.client.get(f"/problem/{self.problem.id}/submissions/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("problem", response.context)
        self.assertEqual(response.context["submissions"], [])


class SubmissionDetailAndCompareTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='u2', password='pass')
        self.problem = Problem.objects.create(
            title='Another Problem',
            statement='desc',
            rating=1300,
            created_at=date.today(),
        )
        self.client.force_login(self.user)

    def _create_submission(self):
        content = b"id,pred\n1,0.1\n"
        f = SimpleUploadedFile("preds.csv", content, content_type="text/csv")
        from runner.models.submission import Submission
        return Submission.objects.create(user=self.user, problem=self.problem, file=f)

    def test_submission_detail_view(self):
        sub = self._create_submission()
        resp = self.client.get(f"/submission/{sub.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "runner/submissions/detail.html")
        self.assertIn("submission", resp.context)
        ctx_sub = resp.context["submission"]
        self.assertTrue(hasattr(ctx_sub, "created_at"))
        self.assertTrue(hasattr(ctx_sub, "metric"))

    def test_submission_compare_requires_ids(self):
        resp = self.client.get(f"/problem/{self.problem.id}/compare/")
        self.assertEqual(resp.status_code, 400)

    def test_submission_compare_ok(self):
        s1 = self._create_submission()
        s2 = self._create_submission()
        url = f"/problem/{self.problem.id}/compare/?ids={s1.id}&ids={s2.id}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "runner/submissions/compare.html")
        self.assertIn("labels", resp.context)
        self.assertIn("metrics", resp.context)
        self.assertEqual(len(resp.context["labels"]), 2)
        self.assertEqual(len(resp.context["metrics"]), 2)
