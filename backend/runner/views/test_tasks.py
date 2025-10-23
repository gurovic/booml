import unittest
from django.test import Client
from django.urls import reverse
from runner.models.task import Task

class TaskListViewTestCase(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        Task.objects.create(title="Task2", created_at="2009-03-15", statement="...", rating=1500)

    def test_task_list_view(self):
        url = reverse("task_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Task2", response.content.decode())
        self.assertIn("1500", response.content.decode())

if __name__ == "__main__": unittest.main()