from datetime import date
import shutil
import tempfile

from django.conf import settings
from django.test import Client, TestCase, override_settings
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

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


class RecentSubmissionsViewTests(TestCase):
    def setUp(self):
        self._media_root = tempfile.mkdtemp()
        self._override_media = override_settings(MEDIA_ROOT=self._media_root)
        self._override_media.enable()
        self.client = Client()
        self.user = User.objects.create_user(username="recent-user", password="pass")
        self.problem = Problem.objects.create(
            title="Recent Problem",
            statement="desc",
            rating=1100,
            created_at=date.today(),
        )

    def tearDown(self):
        self._override_media.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)
        super().tearDown()

    def _create_submission(self):
        content = b"id,pred\n1,0.5\n"
        upload = SimpleUploadedFile("preds.csv", content, content_type="text/csv")
        return Submission.objects.create(user=self.user, problem=self.problem, file=upload)

    def test_recent_submissions_requires_login(self):
        response = self.client.get("/submissions/recent")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))

    def test_recent_submissions_renders_template_with_data(self):
        self.client.force_login(self.user)
        created = [self._create_submission() for _ in range(3)]

        response = self.client.get("/submissions/recent")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "runner/submissions/recent.html")
        context_submissions = list(response.context["submissions"])
        expected_ids = list(
            Submission.objects.filter(user=self.user).order_by("-submitted_at").values_list("id", flat=True)[:3]
        )
        self.assertEqual([s.id for s in context_submissions], expected_ids)
        for submission in context_submissions:
            self.assertIsNotNone(submission.problem)
            self.assertTrue(hasattr(submission, "created_at"))
            self.assertTrue(hasattr(submission, "metric"))

    def test_recent_submissions_limits_results_to_twenty(self):
        self.client.force_login(self.user)
        for _ in range(25):
            self._create_submission()

        response = self.client.get("/submissions/recent")

        self.assertEqual(response.status_code, 200)
        context_submissions = list(response.context["submissions"])
        self.assertEqual(len(context_submissions), 20)
        expected_ids = list(
            Submission.objects.filter(user=self.user).order_by("-submitted_at").values_list("id", flat=True)[:20]
        )
        self.assertEqual([s.id for s in context_submissions], expected_ids)
