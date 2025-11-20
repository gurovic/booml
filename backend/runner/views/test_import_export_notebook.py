import json
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Notebook, Cell


class ImportExportNotebookTests(TestCase):

    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="user", password="pass")
        self.notebook = Notebook.objects.create(owner=self.user, title="Test Notebook")

    def test_export_and_import_notebook_full_cycle(self):

        code_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content='print("Hello")',
            output='Hello',
            execution_order=0
        )
        
        text_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.TEXT,
            content='# Заголовок\n\nТекст',
            output='',
            execution_order=1
        )
        
        latex_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.LATEX,
            content='\\section{Test}',
            output='',
            execution_order=2
        )

        export_url = reverse("runner:export_notebook", args=[self.notebook.id])
        export_response = self.client.get(export_url)

        self.assertEqual(export_response.status_code, 200)
        self.assertIn("application/json", export_response.get("Content-Type", ""))

        exported_data = json.loads(export_response.content.decode('utf-8'))
        
        self.assertIn('notebook', exported_data)
        self.assertIn('cells', exported_data)
        self.assertEqual(exported_data['notebook']['title'], 'Test Notebook')
        self.assertEqual(len(exported_data['cells']), 3)

        json_file = BytesIO(export_response.content)
        json_file.name = 'test_notebook.json'
        
        import_url = reverse("runner:import_notebook")
        import_response = self.client.post(
            import_url,
            {'file': json_file},
            format='multipart'
        )

        self.assertEqual(import_response.status_code, 200)
        import_data = import_response.json()
        self.assertEqual(import_data['status'], 'success')
        self.assertEqual(import_data['cells_created'], 3)
        self.assertEqual(import_data['cells_total'], 3)

        imported_notebook = Notebook.objects.get(id=import_data['notebook_id'])
        self.assertIsNotNone(imported_notebook)
        self.assertEqual(imported_notebook.title, 'Test Notebook')

        imported_cells = imported_notebook.cells.all().order_by('execution_order')
        self.assertEqual(imported_cells.count(), 3)
        
        self.assertEqual(imported_cells[0].cell_type, Cell.CODE)
        self.assertEqual(imported_cells[0].content, 'print("Hello")')
        self.assertEqual(imported_cells[0].output, 'Hello')
        self.assertEqual(imported_cells[0].execution_order, 0)
        
        self.assertEqual(imported_cells[1].cell_type, Cell.TEXT)
        self.assertEqual(imported_cells[1].content, '# Заголовок\n\nТекст')
        self.assertEqual(imported_cells[1].execution_order, 1)
        
        self.assertEqual(imported_cells[2].cell_type, Cell.LATEX)
        self.assertEqual(imported_cells[2].content, '\\section{Test}')
        self.assertEqual(imported_cells[2].execution_order, 2)

    def test_export_and_import_empty_notebook(self):
        export_url = reverse("runner:export_notebook", args=[self.notebook.id])
        export_response = self.client.get(export_url)

        self.assertEqual(export_response.status_code, 200)
        exported_data = json.loads(export_response.content.decode('utf-8'))

        self.assertEqual(len(exported_data['cells']), 0)
        self.assertEqual(exported_data['notebook']['title'], 'Test Notebook')

        json_file = BytesIO(export_response.content)
        json_file.name = 'empty_notebook.json'

        import_url = reverse("runner:import_notebook")
        # передаем owner пользователя при импорте
        import_response = self.client.post(
            import_url,
            {'file': json_file, 'owner_id': self.user.id},  # <-- вот здесь
            format='multipart'
        )

        self.assertEqual(import_response.status_code, 200)
        import_data = import_response.json()
        self.assertEqual(import_data['status'], 'success')
        self.assertEqual(import_data['cells_created'], 0)
        self.assertEqual(import_data['cells_total'], 0)

        imported_notebook = Notebook.objects.get(id=import_data['notebook_id'])
        self.assertEqual(imported_notebook.owner, self.user)  # теперь owner установлен
        self.assertEqual(imported_notebook.cells.count(), 0)

    def test_export_post_returns_json(self):
        Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content='test code',
            execution_order=0
        )

        export_url = reverse("runner:export_notebook", args=[self.notebook.id])
        export_response = self.client.post(export_url)

        self.assertEqual(export_response.status_code, 200)
        response_data = export_response.json()
        
        self.assertEqual(response_data['status'], 'success')
        self.assertIn('data', response_data)
        self.assertIn('filename', response_data)
        
        notebook_data = response_data['data']
        self.assertEqual(notebook_data['notebook']['title'], 'Test Notebook')
        self.assertEqual(len(notebook_data['cells']), 1)
        self.assertEqual(notebook_data['cells'][0]['content'], 'test code')

