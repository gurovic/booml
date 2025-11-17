import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Notebook, Cell


class SaveTextCellTests(TestCase):


    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="creator", password="pass")
        self.notebook = Notebook.objects.create(owner=self.user, title="Test Notebook")
        self.text_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.TEXT,
            content="",
            execution_order=0
        )

    def test_save_text_cell_success_json(self):

        
        response = self.client.post(
            reverse("runner:save_text_cell", args=[self.notebook.id, self.text_cell.id]),
            data=json.dumps({"content": markdown_content}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        

        self.text_cell.refresh_from_db()
        self.assertEqual(self.text_cell.content, markdown_content)

    def test_save_text_cell_success_form_data(self):

        
        response = self.client.post(
            reverse("runner:save_text_cell", args=[self.notebook.id, self.text_cell.id]),
            data={"content": markdown_content}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        
        # Проверяем что контент сохранился
        self.text_cell.refresh_from_db()
        self.assertEqual(self.text_cell.content, markdown_content)

    def test_save_text_cell_updates_content(self):

        # Устанавливаем начальный контент
        self.text_cell.content = "Старый текст"
        self.text_cell.save()

        new_content = "# Новый заголовок\n\nНовый контент."
        response = self.client.post(
            reverse("runner:save_text_cell", args=[self.notebook.id, self.text_cell.id]),
            data=json.dumps({"content": new_content}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.text_cell.refresh_from_db()
        self.assertEqual(self.text_cell.content, new_content)
        self.assertNotEqual(self.text_cell.content, "Старый текст")

    def test_save_text_cell_notebook_not_found(self):

        non_existent_notebook_id = 99999
        
        response = self.client.post(
            reverse("runner:save_text_cell", args=[non_existent_notebook_id, self.text_cell.id]),
            data=json.dumps({"content": "test"}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 404)

    def test_save_text_cell_cell_not_found(self):

        non_existent_cell_id = 99999
        
        response = self.client.post(
            reverse("runner:save_text_cell", args=[self.notebook.id, non_existent_cell_id]),
            data=json.dumps({"content": "test"}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 404)

    def test_save_text_cell_wrong_notebook(self):


        other_notebook = Notebook.objects.create(owner=self.user, title="Other Notebook")
        other_cell = Cell.objects.create(
            notebook=other_notebook,
            cell_type=Cell.TEXT,
            content="",
            execution_order=0
        )


        response = self.client.post(
            reverse("runner:save_text_cell", args=[self.notebook.id, other_cell.id]),
            data=json.dumps({"content": "test"}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 404)

    def test_save_text_cell_empty_content(self):

        response = self.client.post(
            reverse("runner:save_text_cell", args=[self.notebook.id, self.text_cell.id]),
            data=json.dumps({"content": ""}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        
        self.text_cell.refresh_from_db()
        self.assertEqual(self.text_cell.content, "")

    def test_save_text_cell_markdown_content(self):

        complex_markdown = """# Главный заголовок

## Подзаголовок

Это параграф с **жирным** и *курсивным* текстом.

- Пункт списка 1
- Пункт списка 2

```python
def hello():
    print("Hello, World!")
```

[Ссылка](https://example.com)
"""
        
        response = self.client.post(
            reverse("runner:save_text_cell", args=[self.notebook.id, self.text_cell.id]),
            data=json.dumps({"content": complex_markdown}),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.text_cell.refresh_from_db()
        self.assertEqual(self.text_cell.content, complex_markdown)
        self.assertIn("# Главный заголовок", self.text_cell.content)
        self.assertIn("**жирным**", self.text_cell.content)
        self.assertIn("```python", self.text_cell.content)

    def test_save_text_cell_only_post_method(self):

        # GET запрос должен вернуть 405 Method Not Allowed
        response = self.client.get(
            reverse("runner:save_text_cell", args=[self.notebook.id, self.text_cell.id])
        )

        self.assertEqual(response.status_code, 405)

    def test_save_text_cell_multiple_saves(self):

        contents = [
            "Первая версия",
            "Вторая версия",
            "Третья версия"
        ]

        for i, content in enumerate(contents):
            response = self.client.post(
                reverse("runner:save_text_cell", args=[self.notebook.id, self.text_cell.id]),
                data=json.dumps({"content": content}),
                content_type="application/json"
            )
            
            self.assertEqual(response.status_code, 200)
            self.text_cell.refresh_from_db()
            self.assertEqual(self.text_cell.content, content)

