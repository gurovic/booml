import json
from http import HTTPStatus

from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from runner.models import Notebook, Cell
from runner.services import vm_agent, vm_manager
from runner.services.runtime import _sessions, create_session, reset_execution_backend

User = get_user_model()


class RunCellViewTests(TestCase):
    def setUp(self):
        self.sandbox_tmp = TemporaryDirectory()
        self.vm_tmp = TemporaryDirectory()
        reset_execution_backend()
        self.override = override_settings(
            RUNTIME_SANDBOX_ROOT=self.sandbox_tmp.name,
            RUNTIME_VM_ROOT=self.vm_tmp.name,
            RUNTIME_VM_BACKEND="local",
        )
        self.override.enable()
        vm_manager.reset_vm_manager()
        vm_agent.reset_vm_agents()
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.client.login(username="owner", password="pass123")
        self.notebook = Notebook.objects.create(owner=self.user, title="My Notebook")
        self.cell = Cell.objects.create(notebook=self.notebook, cell_type=Cell.CODE, content="x = 2\nprint(x)")
        self.url = reverse("run-cell")
        _sessions.clear()

    def tearDown(self):
        reset_execution_backend()
        vm_manager.reset_vm_manager()
        vm_agent.reset_vm_agents()
        _sessions.clear()
        self.override.disable()
        self.sandbox_tmp.cleanup()
        self.vm_tmp.cleanup()

    def test_run_cell_success(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": self.cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data["stdout"].strip(), "2")
        self.assertIsNone(data["error"])
        self.assertEqual(data["variables"]["x"], "2")

    def test_run_cell_forbidden_for_other_user(self):
        another = User.objects.create_user(username="alien", password="pass456")
        other_nb = Notebook.objects.create(owner=another, title="Other")
        other_cell = Cell.objects.create(notebook=other_nb, cell_type=Cell.CODE, content="print('x')")

        resp = self.client.post(
            self.url,
            {
                "session_id": f"notebook:{other_nb.id}",
                "cell_id": other_cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

    def test_run_cell_not_executable(self):
        latex_cell = Cell.objects.create(notebook=self.notebook, cell_type=Cell.LATEX, content="\\frac{1}{2}")

        resp = self.client.post(
            self.url,
            {
                "session_id": "nb:1",
                "cell_id": latex_cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        body = resp.json()
        self.assertIn("Cell is not executable", json.dumps(body))

    def test_run_cell_without_session_returns_error(self):
        resp = self.client.post(
            self.url,
            {
                "session_id": f"notebook:{self.notebook.id}",
                "cell_id": self.cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("Сессия не создана", resp.json().get("detail", ""))

    def test_run_cell_with_pip_install(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="!pip install requests\nimport sys\nprint('success')"
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertIsNone(data["error"])
        self.assertIn("success", data["stdout"])

    def test_run_cell_with_input_prompt(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="name = input('Name: ')\nprint(f'Hello {name}')",
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data.get("status"), "input_required")
        self.assertIsNotNone(data.get("run_id"))

        follow = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "run_id": data.get("run_id"),
                "stdin": "Alice\n",
            },
        )
        self.assertEqual(follow.status_code, HTTPStatus.OK)
        follow_data = follow.json()
        self.assertEqual(follow_data.get("status"), "success")
        self.assertIsNone(follow_data.get("error"))
        self.assertEqual(follow_data.get("stdout", "").count("Name: "), 1)
        self.assertIn("Hello Alice", follow_data.get("stdout", ""))

    def test_run_cell_invalid_run_id_returns_error(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="name = input('Name: ')\nprint(f'Hello {name}')",
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data.get("status"), "input_required")

        bad = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "run_id": "invalid-run-id",
                "stdin": "Alice\n",
            },
        )
        self.assertEqual(bad.status_code, HTTPStatus.OK)
        bad_data = bad.json()
        self.assertEqual(bad_data.get("status"), "error")
        self.assertIn("run_id", bad_data.get("error", ""))

        follow = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "run_id": data.get("run_id"),
                "stdin": "Alice\n",
            },
        )
        self.assertEqual(follow.status_code, HTTPStatus.OK)
        follow_data = follow.json()
        self.assertEqual(follow_data.get("status"), "success")
        self.assertIn("Hello Alice", follow_data.get("stdout", ""))

    def test_run_cell_with_readline(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="import sys\nline = sys.stdin.readline()\nprint(line.rstrip('\\n'))",
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data.get("status"), "input_required")

        follow = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "run_id": data.get("run_id"),
                "stdin": "123\n",
            },
        )
        self.assertEqual(follow.status_code, HTTPStatus.OK)
        follow_data = follow.json()
        self.assertEqual(follow_data.get("status"), "success")
        self.assertIn("123", follow_data.get("stdout", ""))

    def test_run_cell_with_readline_and_stdin_eof(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="import sys\nprint(sys.stdin.closed)\nline = sys.stdin.readline()\nprint(line == '')\nprint(sys.stdin.closed)",
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data.get("status"), "input_required")
        self.assertEqual(data.get("stdout", "").strip(), "False")

        follow = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "run_id": data.get("run_id"),
                "stdin_eof": True,
            },
        )
        self.assertEqual(follow.status_code, HTTPStatus.OK)
        follow_data = follow.json()
        self.assertEqual(follow_data.get("status"), "success")
        stdout_lines = [line.strip() for line in follow_data.get("stdout", "").splitlines() if line.strip()]
        self.assertEqual(stdout_lines, ["False", "True", "True"])

    def test_run_cell_input_no_echo(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="print(input())",
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data.get("status"), "input_required")

        follow = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "run_id": data.get("run_id"),
                "stdin": "123\n",
            },
        )
        self.assertEqual(follow.status_code, HTTPStatus.OK)
        follow_data = follow.json()
        self.assertEqual(follow_data.get("status"), "success")
        stdout = follow_data.get("stdout", "")
        stdout_lines = [line for line in stdout.splitlines() if line.strip()]
        self.assertEqual(stdout_lines, ["123", "123"])

    def test_run_cell_disallows_stdin_read(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="import sys\nsys.stdin.read()",
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        data = resp.json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("RuntimeError", data.get("error", ""))
        self.assertIn("sys.stdin.read()", data.get("error", ""))

    def test_run_cell_disallows_fileinput(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="import fileinput\nnext(fileinput.input())",
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        data = resp.json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("RuntimeError", data.get("error", ""))
        self.assertIn("fileinput.input()", data.get("error", ""))

    def test_run_cell_error_formatting(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="print('test')\na = 1/0",
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        data = resp.json()
        self.assertEqual(data.get("status"), "error")
        error_text = data.get("error", "")
        self.assertIn("Traceback (most recent call last)", error_text)
        self.assertIn("ZeroDivisionError", error_text)
        self.assertIn("---> 2 a = 1/0", error_text)
        self.assertNotIn("Ошибка:", error_text)

    def test_run_cell_syntax_error_formatting(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="print(123)\nprint('test')\n\nprint(input()\n",
        )
        resp = self.client.post(
            self.url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
            },
        )
        data = resp.json()
        self.assertEqual(data.get("status"), "error")
        error_text = data.get("error", "")
        self.assertIn("SyntaxError", error_text)
        self.assertIn("---> 4 print(input()", error_text)
        self.assertIn("print('test')", error_text)
