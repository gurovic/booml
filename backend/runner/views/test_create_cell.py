import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Notebook, Cell


class CreateCellTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="creator", password="pass")
        self.notebook = Notebook.objects.create(owner=self.user, title="Notebook")

    def test_create_code_cell_default(self):
        response = self.client.post(
            reverse("runner:create_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        cell = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell.cell_type, Cell.CODE)
        self.assertEqual(cell.content, 'print("Hello World")')

    def test_create_latex_cell(self):
        response = self.client.post(
            reverse("runner:create_cell", args=[self.notebook.id]),
            data=json.dumps({"type": "latex"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        cell = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell.cell_type, Cell.LATEX)
        self.assertEqual(cell.content, "")

    def test_create_latex_cell_endpoint(self):
        response = self.client.post(
            reverse("runner:create_latex_cell", args=[self.notebook.id]),
        )

        self.assertEqual(response.status_code, 200)
        cell = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell.cell_type, Cell.LATEX)
