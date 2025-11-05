import unittest
from django.test import Client
from django.urls import reverse
from ..models.task import Task

class TaskListViewTestCase(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        # создаём несколько задач с разными рейтингами
        Task.objects.create(title="Task1", created_at="2009-03-14", statement="...", rating=100)
        Task.objects.create(title="Task2", created_at="2009-03-15", statement="...", rating=200)
        Task.objects.create(title="Task3", created_at="2009-03-16", statement="...", rating=300)

    def _get_url(self):
        # предпочитаем reverse по имени, но оставляем fallback на /runner/tasks/ если name не настроен
        try:
            return reverse("task_list")
        except Exception:
            return "/runner/tasks/"

    def test_task_list_view(self):
        url = self._get_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # ожидаем, что все три задачи отображаются
        self.assertIn("Task1", content)
        self.assertIn("Task2", content)
        self.assertIn("Task3", content)

    def test_min_rating_filters(self):
        url = self._get_url()
        response = self.client.get(url, {"min_rating": "200"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("Task1", content)
        self.assertIn("Task2", content)
        self.assertIn("Task3", content)

    def test_max_rating_filters(self):
        url = self._get_url()
        response = self.client.get(url, {"max_rating": "200"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Task1", content)
        self.assertIn("Task2", content)
        self.assertNotIn("Task3", content)

    def test_min_and_max_filters(self):
        url = self._get_url()
        response = self.client.get(url, {"min_rating": "150", "max_rating": "250"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("Task1", content)
        self.assertIn("Task2", content)
        self.assertNotIn("Task3", content)

    def test_invalid_filters_ignored(self):
        url = self._get_url()
        response = self.client.get(url, {"min_rating": "abc", "max_rating": "---"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # при некорректных фильтрах показываются все задачи
        self.assertIn("Task1", content)
        self.assertIn("Task2", content)
        self.assertIn("Task3", content)

if __name__ == "__main__": unittest.main()
