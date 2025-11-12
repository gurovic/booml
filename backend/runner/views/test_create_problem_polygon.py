from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models.problem import Problem
import json


class CreateProblemPolygonViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="creator", email="creator@example.com", password="pass"
        )
        self.url = reverse("runner:polygon_create_problem")
        self.list_url = reverse("runner:polygon")
        self.login_url = reverse("runner:login")

    def test_get_renders_form_template(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "runner/polygon/problem_create.html")
        self.assertContains(resp, "Создать новую задачу")
        self.assertContains(resp, "name=\"title\"")

    def test_post_html_creates_problem_and_redirects(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.url, {"title": "Моя задача"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.list_url)
        self.assertTrue(Problem.objects.filter(title="Моя задача", author=self.user, is_published=False).exists())

    def test_post_html_empty_title_shows_error_and_no_create(self):
        self.client.force_login(self.user)
        before = Problem.objects.count()
        resp = self.client.post(self.url, {"title": "  "})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "runner/polygon/problem_create.html")
        self.assertContains(resp, "Введите название задачи")
        self.assertEqual(Problem.objects.count(), before)

    def test_post_json_creates_problem_and_returns_id(self):
        self.client.force_login(self.user)
        payload = json.dumps({"title": "JSON задача"})
        resp = self.client.post(self.url, payload, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        pid = data.get("problem_id")
        self.assertIsInstance(pid, int)
        problem = Problem.objects.get(id=pid)
        self.assertEqual(problem.title, "JSON задача")
        self.assertEqual(problem.author, self.user)

    def test_post_json_empty_title_returns_400(self):
        self.client.force_login(self.user)
        payload = json.dumps({"title": "  "})
        resp = self.client.post(self.url, payload, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("title", data.get("message", "").lower())

    def test_title_truncated_to_255_chars(self):
        self.client.force_login(self.user)
        long_title = "A" * 300
        resp = self.client.post(self.url, {"title": long_title})
        self.assertEqual(resp.status_code, 302)
        problem = Problem.objects.latest("id")
        self.assertLessEqual(len(problem.title), 255)

    # --- Новые тесты для неавторизованного пользователя ---
    def test_get_anonymous_renders_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "runner/polygon/problem_create.html")
        self.assertContains(resp, "Создать новую задачу")

    def test_post_html_anonymous_redirects_to_login(self):
        resp = self.client.post(self.url, {"title": "Anon задача"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.login_url)
        self.assertFalse(Problem.objects.filter(title="Anon задача").exists())

    def test_post_json_anonymous_redirects_to_login(self):
        payload = json.dumps({"title": "Anon JSON"})
        resp = self.client.post(self.url, payload, content_type="application/json")
        # Django редирект (302) на страницу логина
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith(self.login_url))
        self.assertFalse(Problem.objects.filter(title="Anon JSON").exists())
