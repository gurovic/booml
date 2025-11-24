# backend/runner/views/test_edit_problem_polygon.py
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from ..models.problem import Problem
from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor


class EditProblemPolygonViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.author = User.objects.create_user(
            username="author", email="author@example.com", password="pass"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )
        self.problem = Problem.objects.create(
            title="Задача 1", rating=900, author=self.author, statement="Исходное"
        )
        self.descriptor = ProblemDescriptor.objects.create(
            problem=self.problem,
            id_column="row_id",
            target_column="prediction",
            id_type="int",
            target_type="float",
            check_order=False,
        )
        self.url = reverse("runner:polygon_edit_problem", args=[self.problem.id])
        self.login_url = reverse("runner:login")

        self._media_dir = tempfile.mkdtemp(prefix="test_media_")
        self._override = override_settings(MEDIA_ROOT=self._media_dir)
        self._override.enable()

    def tearDown(self):
        self._override.disable()
        shutil.rmtree(self._media_dir, ignore_errors=True)
        super().tearDown()

    def _base_post_payload(self, **overrides):
        payload = {
            "title": "Новая задача",
            "rating": "1100",
            "statement": "Новое условие",
            "id_column": "row_id",
            "target_column": "prediction",
            "id_type": "int",
            "target_type": "float",
            "metric_name": "rmse",
            "metric_code": "",
        }
        payload.update(overrides)
        return payload

    def test_get_requires_authentication(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.login_url)

    def test_get_only_author_can_access(self):
        self.client.force_login(self.other_user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 404)

    def test_get_renders_form_with_current_values(self):
        self.client.force_login(self.author)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "runner/polygon/problem_edit.html")
        self.assertContains(resp, "value=\"Задача 1\"")
        self.assertContains(resp, "value=\"900\"")
        self.assertContains(resp, "name=\"id_column\"")
        self.assertContains(resp, "value=\"row_id\"")
        self.assertContains(resp, 'enctype="multipart/form-data"')

    def test_post_valid_data_updates_problem_and_descriptor(self):
        self.client.force_login(self.author)
        resp = self.client.post(
            self.url,
            self._base_post_payload(
                title="Новая задача",
                rating="1200",
                id_column="customer_id",
                target_column="result",
                id_type="str",
                target_type="int",
                check_order="on",
                metric_name="accuracy",
            ),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.url)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.title, "Новая задача")
        self.assertEqual(self.problem.rating, 1200)
        descriptor = ProblemDescriptor.objects.get(problem=self.problem)
        self.assertEqual(descriptor.id_column, "customer_id")
        self.assertEqual(descriptor.target_column, "result")
        self.assertEqual(descriptor.id_type, "str")
        self.assertEqual(descriptor.target_type, "int")
        self.assertTrue(descriptor.check_order)
        self.assertEqual(descriptor.metric_name, "accuracy")
        self.assertFalse(descriptor.metric_code)

    def test_post_invalid_rating_shows_errors(self):
        self.client.force_login(self.author)
        resp = self.client.post(
            self.url,
            self._base_post_payload(rating="5000"),
        )
        self.assertEqual(resp.status_code, 200)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.rating, 900)
        self.assertContains(resp, "Рейтинг должен быть от")

    def test_post_creates_descriptor_if_missing(self):
        ProblemDescriptor.objects.filter(problem=self.problem).delete()
        self.client.force_login(self.author)
        resp = self.client.post(
            self.url,
            self._base_post_payload(id_column="id"),
        )
        self.assertEqual(resp.status_code, 302)
        descriptor = ProblemDescriptor.objects.get(problem=self.problem)
        self.assertEqual(descriptor.id_column, "id")

    def test_metric_name_must_be_known_without_code(self):
        self.client.force_login(self.author)
        resp = self.client.post(
            self.url,
            self._base_post_payload(metric_name="unknown_metric", metric_code=""),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Выберите метрику из списка")

    def test_custom_metric_code_allows_any_name(self):
        self.client.force_login(self.author)
        resp = self.client.post(
            self.url,
            self._base_post_payload(
                metric_name="macro_iou",
                metric_code="def compute_metric(y_true, y_pred):\n    return {'metric': 1.0}",
            ),
        )
        self.assertEqual(resp.status_code, 302)
        descriptor = ProblemDescriptor.objects.get(problem=self.problem)
        self.assertEqual(descriptor.metric_name, "macro_iou")
        self.assertEqual(
            descriptor.metric_code.strip(),
            "def compute_metric(y_true, y_pred):\n    return {'metric': 1.0}",
        )

    def test_upload_problem_files_updates_problem_data(self):
        ProblemData.objects.filter(problem=self.problem).delete()
        self.client.force_login(self.author)
        payload = self._base_post_payload()
        payload.update(
            {
                "train_file": SimpleUploadedFile("train.csv", b"id,label\n1,0\n"),
                "sample_submission_file": SimpleUploadedFile(
                    "sample.csv", b"id,prediction\n1,0.1\n"
                ),
            }
        )

        resp = self.client.post(self.url, payload)

        self.assertEqual(resp.status_code, 302)
        pdata = ProblemData.objects.get(problem=self.problem)
        self.assertTrue(pdata.train_file.name.endswith("train.csv"))
        self.assertTrue(pdata.sample_submission_file.name.endswith("sample.csv"))
