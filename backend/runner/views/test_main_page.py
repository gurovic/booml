from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from runner.models.problem import Problem


class MainPageViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="author", email="author@example.com", password="pass"
        )
        self.published_with_author = Problem.objects.create(
            title="Problem1",
            statement="Statement1",
            created_at="2009-03-15",
            rating=1200,
            author=self.user,
        )
        self.published_without_author = Problem.objects.create(
            title="Problem2",
            statement="Statement2",
            created_at="2009-03-16",
            rating=1300,
        )
        self.unpublished = Problem.objects.create(
            title="Hidden",
            statement="Hidden statement",
            created_at="2009-03-17",
            rating=900,
            is_published=False,
        )

    def test_main_page_view(self):
        url = reverse("runner:main_page")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.published_with_author.title)
        self.assertContains(response, "1200")

    def test_unpublished_tasks_not_listed(self):
        url = reverse("runner:main_page")
        response = self.client.get(url)
        self.assertNotContains(response, self.unpublished.title)

    def test_author_column_shows_username_and_placeholder(self):
        url = reverse("runner:main_page")
        response = self.client.get(url)
        self.assertContains(response, self.user.username)
        self.assertContains(response, "<td>-</td>", html=True)
