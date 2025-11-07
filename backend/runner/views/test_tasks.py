from django.test import Client, TestCase
from django.urls import reverse
from ..models.problem import Problem

class ProblemListViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # создаём несколько задач с разными рейтингами
        Problem.objects.create(title="Problem1", created_at="2009-03-14", statement="...", rating=100)
        Problem.objects.create(title="Problem2", created_at="2009-03-15", statement="...", rating=200)
        Problem.objects.create(title="Problem3", created_at="2009-03-16", statement="...", rating=300)

    def _get_url(self):
        # предпочитаем reverse по имени, но оставляем fallback на /runner/problems/ если name не настроен
        return reverse("runner:problem_list")

    def test_problem_list_view(self):
        url = self._get_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # ожидаем, что все три задачи отображаются
        self.assertIn("Problem1", content)
        self.assertIn("Problem2", content)
        self.assertIn("Problem3", content)

    def test_min_rating_filters(self):
        url = self._get_url()
        response = self.client.get(url, {"min_rating": "200"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("Problem1", content)
        self.assertIn("Problem2", content)
        self.assertIn("Problem3", content)

    def test_max_rating_filters(self):
        url = self._get_url()
        response = self.client.get(url, {"max_rating": "200"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Problem1", content)
        self.assertIn("Problem2", content)
        self.assertNotIn("Problem3", content)

    def test_min_and_max_filters(self):
        url = self._get_url()
        response = self.client.get(url, {"min_rating": "150", "max_rating": "250"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("Problem1", content)
        self.assertIn("Problem2", content)
        self.assertNotIn("Problem3", content)

    def test_invalid_filters_ignored(self):
        url = self._get_url()
        response = self.client.get(url, {"min_rating": "abc", "max_rating": "---"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # при некорректных фильтрах показываются все задачи
        self.assertIn("Problem1", content)
        self.assertIn("Problem2", content)
        self.assertIn("Problem3", content)
