# backend/runner/views/test_edit_problem_polygon.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ..models.problem import Problem
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

    def test_post_valid_data_updates_problem(self):
        self.client.force_login(self.author)
        resp = self.client.post(
            self.url,
            {
                "title": "Новая задача",
                "rating": "1200",
                "statement": "Новое условие",
                "id_column": "customer_id",
                "target_column": "result",
                "id_type": "str",
                "target_type": "int",
                "check_order": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.url)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.title, "Новая задача")
        self.assertEqual(self.problem.rating, 1200)
        self.assertEqual(self.problem.statement, "Новое условие")
        descriptor = ProblemDescriptor.objects.get(problem=self.problem)
        self.assertEqual(descriptor.id_column, "customer_id")
        self.assertEqual(descriptor.target_column, "result")
        self.assertEqual(descriptor.id_type, "str")
        self.assertEqual(descriptor.target_type, "int")
        self.assertTrue(descriptor.check_order)

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

    def test_post_creates_descriptor_if_missing(self):
        ProblemDescriptor.objects.filter(problem=self.problem).delete()
        self.client.force_login(self.author)
        resp = self.client.post(
            self.url,
            {
                "title": "Task descriptor",
                "rating": "1000",
                "statement": "desc",
                "id_column": "id",
                "target_column": "pred",
                "id_type": "int",
                "target_type": "float",
            },
        )
        self.assertEqual(resp.status_code, 302)
        descriptor = ProblemDescriptor.objects.get(problem=self.problem)
        self.assertEqual(descriptor.id_column, "id")
        self.assertEqual(descriptor.target_column, "pred")
