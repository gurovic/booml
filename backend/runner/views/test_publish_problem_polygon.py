import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from ..models.problem import Problem
from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor


class PublishProblemPolygonViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.author = User.objects.create_user(
            username="author", email="author@example.com", password="pass"
        )
        self.other = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )
        self.problem = Problem.objects.create(
            title="Test",
            rating=900,
            statement="Statement",
            author=self.author,
            is_published=False,
        )
        self.descriptor = ProblemDescriptor.objects.create(
            problem=self.problem,
            id_column="id",
            target_column="prediction",
            id_type="int",
            target_type="float",
        )
        self.publish_url = reverse(
            "runner:polygon_publish_problem", args=[self.problem.id]
        )
        self.edit_url = reverse("runner:polygon_edit_problem", args=[self.problem.id])
        self.login_url = reverse("runner:login")

        self._media_dir = tempfile.mkdtemp(prefix="test_media_")
        self._override = override_settings(MEDIA_ROOT=self._media_dir)
        self._override.enable()

    def tearDown(self):
        self._override.disable()
        shutil.rmtree(self._media_dir, ignore_errors=True)
        super().tearDown()

    def _attach_answer_file(self, filename="answer.csv"):
        ProblemData.objects.update_or_create(
            problem=self.problem,
            defaults={
                "answer_file": SimpleUploadedFile(
                    filename, b"id,prediction\n1,0.1\n"
                ),
            },
        )

    def test_requires_authentication(self):
        resp = self.client.post(self.publish_url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.login_url)

    def test_only_author_can_publish(self):
        self.client.force_login(self.other)
        resp = self.client.post(self.publish_url)
        self.assertEqual(resp.status_code, 404)

    def test_validates_required_data_before_publishing(self):
        self.problem.statement = ""
        self.problem.save(update_fields=["statement"])
        ProblemDescriptor.objects.filter(problem=self.problem).delete()

        self.client.force_login(self.author)
        resp = self.client.post(self.publish_url, follow=True)

        self.problem.refresh_from_db()
        self.assertFalse(self.problem.is_published)
        self.assertContains(resp, "Заполните условие задачи")
        self.assertContains(resp, "Заполните описание данных (descriptor)")
        self.assertContains(resp, "Добавьте файл ответов answer.csv")

    def test_rejects_non_csv_answer_file(self):
        self._attach_answer_file(filename="answer.txt")
        self.client.force_login(self.author)
        resp = self.client.post(self.publish_url, follow=True)

        self.problem.refresh_from_db()
        self.assertFalse(self.problem.is_published)
        self.assertContains(resp, "Файл ответов должен быть в формате CSV")

    def test_publishes_problem_with_required_data(self):
        self._attach_answer_file()
        self.client.force_login(self.author)
        resp = self.client.post(self.publish_url, follow=True)

        self.problem.refresh_from_db()
        self.assertTrue(self.problem.is_published)
        self.assertContains(resp, "Задача опубликована")
        self.assertRedirects(resp, self.edit_url)
