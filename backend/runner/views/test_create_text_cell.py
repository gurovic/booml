import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Notebook, Cell


class CreateTextCellTests(TestCase):

    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="creator", password="pass")
        self.notebook = Notebook.objects.create(owner=self.user, title="Test Notebook")
        self.client.force_login(self.user)

    def test_create_text_cell_success(self):
        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.get("Content-Type", ""))
        
        cell = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell.cell_type, Cell.TEXT)
        self.assertEqual(cell.content, "")

    def test_create_text_cell_sets_correct_type(self):
        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        cell = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell.cell_type, Cell.TEXT)
        self.assertIn(Cell.TEXT, [choice[0] for choice in Cell.TYPE_CHOICES])

    def test_create_text_cell_sets_execution_order(self):
        response1 = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )
        self.assertEqual(response1.status_code, 200)
        
        cell1 = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell1.execution_order, 0)

        response2 = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )
        self.assertEqual(response2.status_code, 200)
        
        cells = Cell.objects.filter(notebook=self.notebook).order_by('execution_order')
        self.assertEqual(cells.count(), 2)
        self.assertEqual(cells[0].execution_order, 0)
        self.assertEqual(cells[1].execution_order, 1)

    def test_create_text_cell_notebook_not_found(self):
        non_existent_id = 99999
        response = self.client.post(
            reverse("runner:create_text_cell", args=[non_existent_id])
        )

        self.assertEqual(response.status_code, 404)

    def test_create_text_cell_multiple_cells_order(self):
      

        code_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content='print("test")',
            execution_order=0
        )


        latex_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.LATEX,
            content='\\section{Test}',
            execution_order=1
        )


        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        

        cells = Cell.objects.filter(notebook=self.notebook).order_by('execution_order')
        self.assertEqual(cells.count(), 3)
        self.assertEqual(cells[0].cell_type, Cell.CODE)
        self.assertEqual(cells[1].cell_type, Cell.LATEX)
        self.assertEqual(cells[2].cell_type, Cell.TEXT)
        self.assertEqual(cells[2].execution_order, 2)

    def test_create_text_cell_returns_html_template(self):

        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(b'data-cell-type="text"', response.content)
        self.assertIn(b'data-text-container', response.content)
        self.assertIn(b'text-cell', response.content)

    def test_create_text_cell_empty_notebook(self):


        self.assertEqual(Cell.objects.filter(notebook=self.notebook).count(), 0)

        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        cell = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell.execution_order, 0)

    def test_create_text_cell_forbidden_for_other_user(self):
        """Проверка, что другой пользователь не может создать ячейку в чужом блокноте"""
        other_user = get_user_model().objects.create_user(username="other", password="pass")
        self.client.force_login(other_user)
        
        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Cell.objects.filter(notebook=self.notebook).count(), 0)

    def test_create_text_cell_allowed_for_notebook_for_user(self):
        """Проверка, что можно создать ячейку в блокноте для владельца"""
        # используем существующего пользователя self.user
        notebook_for_user = Notebook.objects.create(owner=self.user, title="User's Notebook")

        response = self.client.post(
            reverse("runner:create_text_cell", args=[notebook_for_user.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cell.objects.filter(notebook=notebook_for_user).count(), 1)

