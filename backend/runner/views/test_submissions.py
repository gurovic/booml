from datetime import date
import shutil
import tempfile

from django.conf import settings
from django.test import Client, TestCase, override_settings
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from runner.views.submissions import _primary_metric, extract_labels_and_metrics
from runner.models.problem import Problem
from runner.models.submission import Submission


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

    @patch("runner.views.submissions.Submission")
    def test_submission_list_iteration_exception(self, mock_submission):
        mock_qs = MagicMock()
        mock_submission.objects.filter.return_value = mock_qs
        mock_qs.exists.return_value = True
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__iter__.side_effect = Exception("Database error")

        response = self.client.get(f"/problem/{self.problem.id}/submissions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["submissions"], [])

    @patch("runner.views.submissions.Submission")
    def test_submission_list_exists_exception(self, mock_submission):
        mock_qs = MagicMock()
        mock_submission.objects.filter.return_value = mock_qs
        mock_qs.exists.side_effect = Exception("Exists failed")
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__iter__.return_value = []

        response = self.client.get(f"/problem/{self.problem.id}/submissions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["submissions"], [])

    @patch("runner.views.submissions.render")
    @patch("runner.views.submissions.Submission")
    def test_submission_list_with_different_statuses(self, mock_submission, mock_render):
        mock_submission1 = MagicMock()
        mock_submission1.status = "accepted"
        mock_submission1.metrics = {"metric": 0.8}
        mock_submission1.submitted_at = date.today()

        mock_submission2 = MagicMock()
        mock_submission2.status = "failed"
        mock_submission2.metrics = {"metric": 0.5}
        mock_submission2.submitted_at = date.today()

        mock_qs = MagicMock()
        mock_submission.objects.filter.return_value = mock_qs
        mock_qs.exists.return_value = True
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__iter__.return_value = [mock_submission1, mock_submission2]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_render.return_value = mock_response

        from runner.views.submissions import submission_list
        request = MagicMock()
        request.user = self.user
        response = submission_list(request, self.problem.id)

        call_args = mock_render.call_args
        context = call_args[0][2]
        self.assertEqual(context["result"]["status"], "OK")


class SubmissionDetailAndCompareTests(TestCase):
    def setUp(self):
        self._media_root = tempfile.mkdtemp()
        self._override_media = override_settings(MEDIA_ROOT=self._media_root)
        self._override_media.enable()
        self.client = Client()
        self.user = User.objects.create_user(username='u2', password='pass')
        self.problem = Problem.objects.create(
            title='Another Problem',
            statement='desc',
            rating=1300,
            created_at=date.today(),
        )
        self.client.force_login(self.user)
    
    def tearDown(self):
        self._override_media.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)
        super().tearDown()

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

    def test_submission_compare_invalid_ids(self):
        url = f"/problem/{self.problem.id}/compare/?ids=invalid&ids=123abc"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 400)

    def test_submission_compare_no_permission(self):
        other_user = User.objects.create_user(username='other', password='pass')
        other_problem = Problem.objects.create(title='Other', statement='desc', rating=1000)

        content = b"id,pred\n1,0.1\n"
        f = SimpleUploadedFile("other.csv", content, content_type="text/csv")
        from runner.models.submission import Submission
        other_sub = Submission.objects.create(user=other_user, problem=other_problem, file=f)

        url = f"/problem/{self.problem.id}/compare/?ids={other_sub.id}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["submissions"]), 0)


class PrimaryMetricTests(TestCase):
    def test_primary_metric_none(self):
        self.assertIsNone(_primary_metric(None))

    def test_primary_metric_number(self):
        self.assertEqual(_primary_metric(42), 42.0)
        self.assertEqual(_primary_metric(3.14), 3.14)

    def test_primary_metric_dict(self):
        self.assertEqual(_primary_metric({"metric": 0.8}), 0.8)
        self.assertEqual(_primary_metric({"score": 0.9}), 0.9)
        self.assertEqual(_primary_metric({"accuracy": 0.95}), 0.95)
        self.assertEqual(_primary_metric({"f1": 0.85}), 0.85)
        self.assertEqual(_primary_metric({"auc": 0.75}), 0.75)
        self.assertEqual(_primary_metric({"other": 0.5}), 0.5)
        self.assertIsNone(_primary_metric({"invalid": "text"}))

    def test_primary_metric_list(self):
        self.assertEqual(_primary_metric([0.7, 0.8]), 0.7)
        self.assertEqual(_primary_metric(["text", 0.8]), 0.8)
        self.assertIsNone(_primary_metric(["text1", "text2"]))

    def test_primary_metric_string(self):
        self.assertIsNone(_primary_metric("invalid"))
        self.assertEqual(_primary_metric("0.8"), 0.8)


class ExtractLabelsAndMetricsTests(TestCase):
    def test_extract_labels_and_metrics(self):
        mock_sub1 = MagicMock()
        mock_sub1.created_at = None
        mock_sub1.metric = 0.8

        mock_sub2 = MagicMock()
        mock_sub2.created_at = date(2023, 1, 15)
        mock_sub2.metric = None

        mock_sub3 = MagicMock()
        mock_sub3.created_at = date(2023, 1, 16)
        mock_sub3.metric = 0.9

        labels, metrics = extract_labels_and_metrics([mock_sub1, mock_sub2, mock_sub3])

        self.assertEqual(labels, ["-", "15.01 00:00", "16.01 00:00"])
        self.assertEqual(metrics, [0.8, 0, 0.9])
