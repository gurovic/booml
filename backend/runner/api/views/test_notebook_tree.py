from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from runner.models import Cell, Notebook, NotebookFolder, Problem

User = get_user_model()


class NotebookTreeAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pass123")
        self.other_user = User.objects.create_user(username="bob", password="pass123")
        self.client.login(username="alice", password="pass123")

        self.problem = Problem.objects.create(title="Tree problem", statement="statement")
        self.problem_notebook = Notebook.objects.create(
            owner=self.user,
            problem=self.problem,
            title="Problem notebook",
        )
        self.custom_folder = NotebookFolder.objects.create(
            owner=self.user,
            title="Research",
            kind=NotebookFolder.Kind.CUSTOM,
        )
        self.custom_notebook = Notebook.objects.create(
            owner=self.user,
            folder=self.custom_folder,
            title="Folder notebook",
        )
        self.root_notebook = Notebook.objects.create(owner=self.user, title="Root notebook")

        self.tree_url = reverse("notebook-tree")
        self.create_folder_url = reverse("notebook-folder-create")
        self.folder_move_url = reverse("notebook-folder-move", args=[self.custom_folder.id])
        self.notebook_move_url = reverse("notebook-move", args=[self.root_notebook.id])

    def test_tree_returns_folders_and_backfills_problem_notebooks(self):
        Cell.objects.create(
            notebook=self.custom_notebook,
            cell_type=Cell.CODE,
            content="print('hello')",
            output="hello",
            execution_order=0,
        )
        response = self.client.get(self.tree_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        payload = response.json()

        folders = payload["folders"]
        tasks_folder = next(folder for folder in folders if folder["kind"] == NotebookFolder.Kind.TASKS)
        self.assertTrue(tasks_folder["is_system"])
        self.assertEqual(tasks_folder["title"], NotebookFolder.SYSTEM_TASK_FOLDER_TITLE)
        self.assertIsNone(tasks_folder["parent_id"])
        self.assertIn("created_at", tasks_folder)
        self.assertIn("size_bytes", tasks_folder)
        self.assertEqual(payload["tasks_folder_id"], tasks_folder["id"])

        notebooks_by_id = {item["id"]: item for item in payload["notebooks"]}
        self.assertEqual(notebooks_by_id[self.problem_notebook.id]["folder_id"], tasks_folder["id"])
        self.assertEqual(notebooks_by_id[self.custom_notebook.id]["folder_id"], self.custom_folder.id)
        self.assertIsNone(notebooks_by_id[self.root_notebook.id]["folder_id"])
        self.assertIn("created_at", notebooks_by_id[self.custom_notebook.id])
        self.assertIn("size_bytes", notebooks_by_id[self.custom_notebook.id])
        self.assertGreater(notebooks_by_id[self.custom_notebook.id]["size_bytes"], 0)

        custom_folder_payload = next(folder for folder in folders if folder["id"] == self.custom_folder.id)
        self.assertGreaterEqual(
            custom_folder_payload["size_bytes"],
            notebooks_by_id[self.custom_notebook.id]["size_bytes"],
        )

        self.problem_notebook.refresh_from_db()
        self.assertEqual(self.problem_notebook.folder_id, tasks_folder["id"])

    def test_create_folder(self):
        response = self.client.post(
            self.create_folder_url,
            {"title": "New folder"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        payload = response.json()
        self.assertEqual(payload["title"], "New folder")
        self.assertEqual(payload["kind"], NotebookFolder.Kind.CUSTOM)
        self.assertFalse(payload["is_system"])
        self.assertIsNone(payload["parent_id"])

    def test_create_nested_folder(self):
        response = self.client.post(
            self.create_folder_url,
            {"title": "Nested", "parent_id": self.custom_folder.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        payload = response.json()
        self.assertEqual(payload["parent_id"], self.custom_folder.id)

        folder = NotebookFolder.objects.get(pk=payload["id"])
        self.assertEqual(folder.parent_id, self.custom_folder.id)

    def test_create_folder_with_foreign_parent_is_forbidden(self):
        foreign_parent = NotebookFolder.objects.create(
            owner=self.other_user,
            title="Private parent",
            kind=NotebookFolder.Kind.CUSTOM,
        )
        response = self.client.post(
            self.create_folder_url,
            {"title": "Nested", "parent_id": foreign_parent.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_create_folder_inside_tasks_folder_is_forbidden(self):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(self.user)
        response = self.client.post(
            self.create_folder_url,
            {"title": "Nested", "parent_id": tasks_folder.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_rename_custom_folder(self):
        detail_url = reverse("notebook-folder-detail", args=[self.custom_folder.id])
        response = self.client.patch(
            detail_url,
            {"title": "Renamed folder"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.custom_folder.refresh_from_db()
        self.assertEqual(self.custom_folder.title, "Renamed folder")

    def test_rename_tasks_folder_is_forbidden(self):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(self.user)
        detail_url = reverse("notebook-folder-detail", args=[tasks_folder.id])
        response = self.client.patch(
            detail_url,
            {"title": "New title"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_delete_custom_folder_removes_subtree_and_notebooks(self):
        nested_folder = NotebookFolder.objects.create(
            owner=self.user,
            parent=self.custom_folder,
            title="Nested",
            kind=NotebookFolder.Kind.CUSTOM,
        )
        nested_notebook = Notebook.objects.create(
            owner=self.user,
            folder=nested_folder,
            title="Nested notebook",
        )

        detail_url = reverse("notebook-folder-detail", args=[self.custom_folder.id])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertFalse(Notebook.objects.filter(id=self.custom_notebook.id).exists())
        self.assertFalse(Notebook.objects.filter(id=nested_notebook.id).exists())
        self.assertFalse(NotebookFolder.objects.filter(id=nested_folder.id).exists())
        self.assertFalse(NotebookFolder.objects.filter(id=self.custom_folder.id).exists())
        self.assertTrue(Notebook.objects.filter(id=self.root_notebook.id).exists())

    def test_delete_tasks_folder_is_forbidden(self):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(self.user)
        detail_url = reverse("notebook-folder-detail", args=[tasks_folder.id])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_move_folder(self):
        target = NotebookFolder.objects.create(
            owner=self.user,
            title="Target",
            kind=NotebookFolder.Kind.CUSTOM,
        )
        response = self.client.patch(
            self.folder_move_url,
            {"parent_id": target.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.custom_folder.refresh_from_db()
        self.assertEqual(self.custom_folder.parent_id, target.id)

    def test_cannot_move_tasks_folder(self):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(self.user)
        move_url = reverse("notebook-folder-move", args=[tasks_folder.id])
        response = self.client.patch(
            move_url,
            {"parent_id": self.custom_folder.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_cannot_move_folder_to_tasks_folder(self):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(self.user)
        response = self.client.patch(
            self.folder_move_url,
            {"parent_id": tasks_folder.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_cannot_move_folder_from_tasks_subtree(self):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(self.user)
        inside_tasks_folder = NotebookFolder.objects.create(
            owner=self.user,
            parent=tasks_folder,
            title="Inside tasks",
            kind=NotebookFolder.Kind.CUSTOM,
        )
        move_url = reverse("notebook-folder-move", args=[inside_tasks_folder.id])
        response = self.client.patch(
            move_url,
            {"parent_id": None},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_move_notebook(self):
        response = self.client.patch(
            self.notebook_move_url,
            {"folder_id": self.custom_folder.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.root_notebook.refresh_from_db()
        self.assertEqual(self.root_notebook.folder_id, self.custom_folder.id)

    def test_cannot_move_notebook_to_tasks_folder(self):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(self.user)
        response = self.client.patch(
            self.notebook_move_url,
            {"folder_id": tasks_folder.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_cannot_move_notebook_to_tasks_subfolder(self):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(self.user)
        tasks_subfolder = NotebookFolder.objects.create(
            owner=self.user,
            parent=tasks_folder,
            title="Tasks child",
            kind=NotebookFolder.Kind.CUSTOM,
        )
        response = self.client.patch(
            self.notebook_move_url,
            {"folder_id": tasks_subfolder.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_cannot_move_notebook_from_tasks_folder(self):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(self.user)
        self.root_notebook.folder = tasks_folder
        self.root_notebook.save(update_fields=["folder", "updated_at"])

        response = self.client.patch(
            self.notebook_move_url,
            {"folder_id": self.custom_folder.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_other_user_folder_is_hidden(self):
        foreign_folder = NotebookFolder.objects.create(
            owner=self.other_user,
            title="Private folder",
            kind=NotebookFolder.Kind.CUSTOM,
        )
        detail_url = reverse("notebook-folder-detail", args=[foreign_folder.id])
        response = self.client.patch(
            detail_url,
            {"title": "Hacked"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
