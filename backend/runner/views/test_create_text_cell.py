import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Notebook, Cell


class CreateTextCellTests(TestCase):
    """Тесты для создания текстовых ячеек с Markdown"""

    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="creator", password="pass")
        self.notebook = Notebook.objects.create(owner=self.user, title="Test Notebook")

    def test_create_text_cell_success(self):
        """Тест успешного создания текстовой ячейки"""
        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.get("Content-Type", ""))
        
        # Проверяем что ячейка создана
        cell = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell.cell_type, Cell.TEXT)
        self.assertEqual(cell.content, "")

    def test_create_text_cell_sets_correct_type(self):
        """Тест что ячейка создается с правильным типом TEXT"""
        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        cell = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell.cell_type, Cell.TEXT)
        self.assertIn(Cell.TEXT, [choice[0] for choice in Cell.TYPE_CHOICES])

    def test_create_text_cell_sets_execution_order(self):
        """Тест что ячейка получает правильный порядковый номер"""
        # Создаем первую ячейку
        response1 = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )
        self.assertEqual(response1.status_code, 200)
        
        cell1 = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell1.execution_order, 0)

        # Создаем вторую ячейку
        response2 = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )
        self.assertEqual(response2.status_code, 200)
        
        cells = Cell.objects.filter(notebook=self.notebook).order_by('execution_order')
        self.assertEqual(cells.count(), 2)
        self.assertEqual(cells[0].execution_order, 0)
        self.assertEqual(cells[1].execution_order, 1)

    def test_create_text_cell_notebook_not_found(self):
        """Тест обработки несуществующего блокнота"""
        non_existent_id = 99999
        response = self.client.post(
            reverse("runner:create_text_cell", args=[non_existent_id])
        )

        self.assertEqual(response.status_code, 404)

    def test_create_text_cell_multiple_cells_order(self):
        """Тест создания нескольких ячеек с правильным порядком"""
        # Создаем код ячейку
        code_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content='print("test")',
            execution_order=0
        )

        # Создаем LaTeX ячейку
        latex_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.LATEX,
            content='\\section{Test}',
            execution_order=1
        )

        # Создаем текстовую ячейку
        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        
        # Проверяем порядок
        cells = Cell.objects.filter(notebook=self.notebook).order_by('execution_order')
        self.assertEqual(cells.count(), 3)
        self.assertEqual(cells[0].cell_type, Cell.CODE)
        self.assertEqual(cells[1].cell_type, Cell.LATEX)
        self.assertEqual(cells[2].cell_type, Cell.TEXT)
        self.assertEqual(cells[2].execution_order, 2)

    def test_create_text_cell_returns_html_template(self):
        """Тест что возвращается правильный HTML шаблон"""
        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        # Проверяем что в ответе есть элементы текстовой ячейки
        self.assertIn(b'data-cell-type="text"', response.content)
        self.assertIn(b'data-text-container', response.content)
        self.assertIn(b'text-cell', response.content)

    def test_create_text_cell_empty_notebook(self):
        """Тест создания первой ячейки в пустом блокноте"""
        # Убеждаемся что блокнот пустой
        self.assertEqual(Cell.objects.filter(notebook=self.notebook).count(), 0)

        response = self.client.post(
            reverse("runner:create_text_cell", args=[self.notebook.id])
        )

        self.assertEqual(response.status_code, 200)
        cell = Cell.objects.get(notebook=self.notebook)
        self.assertEqual(cell.execution_order, 0)

