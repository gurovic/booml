import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Notebook


class RenameNotebookViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="testuser", password="pass")
        self.notebook = Notebook.objects.create(owner=self.user, title="Initial title")

    def test_successful_rename(self):
        response = self.client.patch(
            reverse("runner:rename_notebook", args=[self.notebook.id]),
            data=json.dumps({"title": "Updated title"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["title"], "Updated title")

        self.notebook.refresh_from_db()
        self.assertEqual(self.notebook.title, "Updated title")

    def test_rejects_empty_title(self):
        response = self.client.post(
            reverse("runner:rename_notebook", args=[self.notebook.id]),
            data=json.dumps({"title": "   "}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertIn("не может быть пустым", payload["message"])

        self.notebook.refresh_from_db()
        self.assertEqual(self.notebook.title, "Initial title")

    def test_form_submission_updates_title(self):
        response = self.client.post(
            reverse("runner:rename_notebook", args=[self.notebook.id]),
            data={"title": "Form based title"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.notebook.refresh_from_db()
        self.assertEqual(self.notebook.title, "Form based title")
