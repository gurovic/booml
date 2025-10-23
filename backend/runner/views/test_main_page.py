from django.test import TestCase, Client
from django.urls import reverse
from runner.models.task import Task

class MainPageViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        Task.objects.create(title="Task1", statement="Statement1", created_at="2009-03-15", rating=1200)

    def test_main_page_view(self):
        url = reverse("main_page")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task1")
        self.assertContains(response, "1200")
