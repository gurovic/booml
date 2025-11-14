# backend/runner/views/test_edit_problem_polygon.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ..models.problem import Problem


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
        self.url = reverse("runner:polygon_edit_problem", args=[self.problem.id])
        self.login_url = reverse("runner:login")

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

    def test_post_valid_data_updates_problem(self):
        self.client.force_login(self.author)
        resp = self.client.post(
            self.url,
            {
                "title": "Новая задача",
                "rating": "1200",
                "statement": "Новое условие",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.url)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.title, "Новая задача")
        self.assertEqual(self.problem.rating, 1200)
        self.assertEqual(self.problem.statement, "Новое условие")

    def test_post_invalid_rating_shows_errors(self):
        self.client.force_login(self.author)
        resp = self.client.post(
            self.url,
            {
                "title": "Новая задача",
                "rating": "5000",
                "statement": "Новое условие",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.rating, 900)
        self.assertContains(resp, "Рейтинг должен быть от")
