from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from runner.models import Notebook


User = get_user_model()


class NotebookListViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Пользователи
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

        # Блокноты user1
        self.nb1_u1 = Notebook.objects.create(owner=self.user1, title="U1 NB1")
        self.nb2_u1 = Notebook.objects.create(owner=self.user1, title="U1 NB2")

        # Блокнот user2
        self.nb1_u2 = Notebook.objects.create(owner=self.user2, title="U2 NB1")

    def test_user_sees_only_their_notebooks(self):
        """Авторизованный пользователь видит только свои блокноты"""
        self.client.login(username="user1", password="pass")

        url = reverse("runner:notebook_list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # пользователь видит свои 2 блокнота
        self.assertContains(response, "U1 NB1")
        self.assertContains(response, "U1 NB2")

        # но НЕ видит чужой
        self.assertNotContains(response, "U2 NB1")

    def test_other_user_sees_only_their_own_notebooks(self):
        """Второй пользователь также видит только свои блокноты"""
        self.client.login(username="user2", password="pass")

        url = reverse("runner:notebook_list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "U2 NB1")
        self.assertNotContains(response, "U1 NB1")
        self.assertNotContains(response, "U1 NB2")

    def test_anonymous_user_redirects_to_login(self):
        """Анонимный пользователь должен быть перенаправлен на логин"""
        url = reverse("runner:notebook_list")
        response = self.client.get(url)

        # если login_required включён — будет redirect
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)
