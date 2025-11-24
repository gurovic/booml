import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Cell, Notebook


class BaseNotebookTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="author", password="pass")
        self.notebook = Notebook.objects.create(owner=self.user, title="Notebook")


class CopyCellViewTests(BaseNotebookTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.first = Cell.objects.create(
            notebook=self.notebook, cell_type=Cell.CODE, content="print(1)", output="old", execution_order=0
        )
        self.second = Cell.objects.create(
            notebook=self.notebook, cell_type=Cell.CODE, content="print(2)", execution_order=1
        )

    def test_copy_cell_inserts_after_source_by_default(self):
        response = self.client.post(
            reverse("runner:copy_cell", args=[self.notebook.id, self.first.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")

        new_cell = Cell.objects.get(pk=payload["cell_id"])
        self.assertEqual(new_cell.cell_type, Cell.CODE)
        self.assertEqual(new_cell.content, self.first.content)
        self.assertEqual(new_cell.output, "")

        ordered_ids = list(self.notebook.cells.order_by("execution_order").values_list("id", flat=True))
        self.assertEqual(ordered_ids, [self.first.id, new_cell.id, self.second.id])

    def test_copy_cell_rejects_invalid_position(self):
        response = self.client.post(
            reverse("runner:copy_cell", args=[self.notebook.id, self.first.id]),
            data=json.dumps({"target_position": 99}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["status"], "error")

    def test_copy_cell_allows_explicit_target(self):
        response = self.client.post(
            reverse("runner:copy_cell", args=[self.notebook.id, self.second.id]),
            data=json.dumps({"target_position": 0}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        new_id = payload["cell_id"]

        ordered_ids = list(self.notebook.cells.order_by("execution_order").values_list("id", flat=True))
        self.assertEqual(len(ordered_ids), 3)
        # Новый элемент теперь первый
        self.assertEqual(ordered_ids[0], new_id)
        self.assertEqual(ordered_ids[1], self.first.id)

    def test_copy_cell_preserves_cell_type(self):
        latex = Cell.objects.create(
            notebook=self.notebook, cell_type=Cell.LATEX, content="\\frac{1}{2}", execution_order=2
        )
        response = self.client.post(
            reverse("runner:copy_cell", args=[self.notebook.id, latex.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        new_cell = Cell.objects.get(pk=payload["cell_id"])
        self.assertEqual(new_cell.cell_type, Cell.LATEX)
        self.assertEqual(new_cell.content, latex.content)


class MoveCellViewTests(BaseNotebookTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.first = Cell.objects.create(
            notebook=self.notebook, cell_type=Cell.CODE, content="a", execution_order=0
        )
        self.second = Cell.objects.create(
            notebook=self.notebook, cell_type=Cell.CODE, content="b", execution_order=1
        )
        self.third = Cell.objects.create(
            notebook=self.notebook, cell_type=Cell.CODE, content="c", execution_order=2
        )

    def test_move_cell_to_first_position(self):
        response = self.client.patch(
            reverse("runner:move_cell", args=[self.notebook.id, self.third.id]),
            data=json.dumps({"target_position": 0}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")

        ordered_ids = list(self.notebook.cells.order_by("execution_order").values_list("id", flat=True))
        self.assertEqual(ordered_ids, [self.third.id, self.first.id, self.second.id])

    def test_move_cell_rejects_out_of_range(self):
        response = self.client.patch(
            reverse("runner:move_cell", args=[self.notebook.id, self.second.id]),
            data=json.dumps({"target_position": 10}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
