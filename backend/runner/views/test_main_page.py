from django.test import TestCase, Client
from django.urls import reverse
from runner.models.problem import Problem

class MainPageViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.published = Problem.objects.create(
            title="Problem1", statement="Statement1", created_at="2009-03-15", rating=1200
        )
        self.unpublished = Problem.objects.create(
            title="Hidden",
            statement="Hidden statement",
            created_at="2009-03-16",
            rating=1300,
            is_published=False,
        )

    def test_main_page_view(self):
        url = reverse("runner:main_page")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Problem1")
        self.assertContains(response, "1200")
    def test_unpublished_tasks_not_listed(self):
        url = reverse("runner:main_page")
        response = self.client.get(url)
        self.assertContains(response, self.published.title)
        self.assertNotContains(response, self.unpublished.title)
