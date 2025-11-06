from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Notebook


class DeleteNotebookViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="user", password="pass")
        self.notebook = Notebook.objects.create(owner=self.user, title="Notebook to delete")

    def test_html_form_deletes_notebook(self):
        response = self.client.post(
            reverse("runner:delete_notebook", args=[self.notebook.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Notebook.objects.filter(id=self.notebook.id).exists())

    def test_ajax_delete_returns_json(self):
        response = self.client.delete(
            reverse("runner:delete_notebook", args=[self.notebook.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertFalse(Notebook.objects.filter(id=self.notebook.id).exists())
