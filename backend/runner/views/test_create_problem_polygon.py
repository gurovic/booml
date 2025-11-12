# backend/runner/views/test_create_problem_polygon.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models.problem import Problem

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
        # Авторизованный GET
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "runner/polygon/problem_create.html")
        self.assertContains(resp, "Создать новую задачу")
        self.assertContains(resp, "name=\"title\"")

    def test_get_anonymous_renders_form(self):
        # Анонимный GET тоже видит форму
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "runner/polygon/problem_create.html")
        self.assertContains(resp, "Создать новую задачу")

    def test_post_html_creates_problem_and_redirects(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.url, {"title": "Моя задача"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.list_url)
        self.assertTrue(
            Problem.objects.filter(title="Моя задача", author=self.user, is_published=False).exists()
        )

    def test_post_html_empty_title_shows_error_and_no_create(self):
        self.client.force_login(self.user)
        before = Problem.objects.count()
        resp = self.client.post(self.url, {"title": "   "})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "runner/polygon/problem_create.html")
        self.assertEqual(Problem.objects.count(), before)

    def test_post_html_anonymous_redirects_to_login(self):
        resp = self.client.post(self.url, {"title": "Anon задача"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.login_url)
        self.assertFalse(Problem.objects.filter(title="Anon задача").exists())
