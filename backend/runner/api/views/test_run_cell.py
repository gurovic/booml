import json
from http import HTTPStatus
import time

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
        self.input_url = reverse("run-cell-input")
        self.stream_start_url = reverse("run-cell-stream-start")
        self.stream_status_url = reverse("run-cell-stream-status")
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
        self.assertIn("outputs", data)

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

    def test_run_cell_returns_rich_outputs(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="import pandas as pd\npd.DataFrame({'a': [1, 2]})"
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
        outputs = data.get("outputs") or []
        types = {item.get("type") for item in outputs}
        self.assertIn("text/html", types)

    def test_run_cell_stream_success(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)

        start_resp = self.client.post(
            self.stream_start_url,
            {
                "session_id": session_id,
                "cell_id": self.cell.id,
            },
        )
        self.assertEqual(start_resp.status_code, HTTPStatus.OK)
        run_id = start_resp.json().get("run_id")
        self.assertTrue(run_id)

        stdout_offset = 0
        stderr_offset = 0
        finished = False
        for _ in range(40):
            status_resp = self.client.get(
                f"{self.stream_status_url}?run_id={run_id}&stdout_offset={stdout_offset}&stderr_offset={stderr_offset}"
            )
            self.assertEqual(status_resp.status_code, HTTPStatus.OK)
            payload = status_resp.json()
            stdout_offset = payload.get("stdout_offset", stdout_offset)
            stderr_offset = payload.get("stderr_offset", stderr_offset)
            if payload.get("status") == "finished":
                result = payload.get("result") or {}
                self.assertIn("2", (result.get("stdout") or ""))
                finished = True
                break
            time.sleep(0.05)

        self.assertTrue(finished)

    def test_run_cell_stream_missing_session_returns_error(self):
        start_resp = self.client.post(
            self.stream_start_url,
            {
                "session_id": f"notebook:{self.notebook.id}",
                "cell_id": self.cell.id,
            },
        )
        self.assertEqual(start_resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("Сессия не создана", start_resp.json().get("detail", ""))

    def test_run_cell_with_input_prompt(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="name = input('Hello: ')\nprint(f'Hello {name}')",
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
        self.assertEqual(data.get("prompt"), "Hello: ")
        self.assertIn("Hello: ", data.get("stdout", ""))
        self.assertEqual(data.get("stdout", "").count("Hello: "), 1)

        resp = self.client.post(
            self.input_url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "run_id": data.get("run_id"),
                "input": "Ada",
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("Hello Ada", data.get("stdout", ""))

    def test_run_cell_print_input_echoes(self):
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

        resp = self.client.post(
            self.input_url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "run_id": data.get("run_id"),
                "input": "1234",
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        stdout = data.get("stdout", "")
        self.assertEqual(stdout.count("1234"), 2)

    def test_run_cell_with_readline_and_stdin_eof(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="import sys\nline = sys.stdin.readline()\nprint(line == \"\")\nprint(sys.stdin.closed)",
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

        resp = self.client.post(
            self.input_url,
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "run_id": data.get("run_id"),
                "stdin_eof": True,
            },
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertIn("True", data.get("stdout", ""))

    def test_run_cell_blocked_stdin_read_and_fileinput(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="import sys, fileinput\n"
                    "try:\n"
                    "    sys.stdin.read()\n"
                    "except RuntimeError as exc:\n"
                    "    print(exc)\n"
                    "try:\n"
                    "    next(fileinput.input())\n"
                    "except RuntimeError as exc:\n"
                    "    print(exc)\n",
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
        self.assertIn("sys.stdin.read()", data.get("stdout", ""))
        self.assertIn("fileinput.input()", data.get("stdout", ""))
