import io
import builtins
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from django.test import TestCase

from .vm_agent import _handle_shell_commands, start_interactive_run


class ShellCommandHandlingTests(TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.workdir = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_handle_pip_install_command(self):
        code = "!pip install requests\nprint('done')"
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        
        filtered_code = _handle_shell_commands(
            code, self.workdir, stdout_buf, stderr_buf
        )
        
        self.assertNotIn("!pip", filtered_code)
        self.assertIn("print('done')", filtered_code)
        stdout_output = stdout_buf.getvalue()
        self.assertTrue(len(stdout_output) > 0 or len(stderr_buf.getvalue()) > 0)

    def test_handle_multiple_pip_install_commands(self):
        code = "!pip install requests\n!pip install numpy\nprint('done')"
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        
        filtered_code = _handle_shell_commands(
            code, self.workdir, stdout_buf, stderr_buf
        )
        
        self.assertNotIn("!pip", filtered_code)
        self.assertIn("print('done')", filtered_code)

    def test_preserve_non_pip_commands(self):
        code = "x = 1\n!pip install requests\ny = 2\nprint(x + y)"
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        
        filtered_code = _handle_shell_commands(
            code, self.workdir, stdout_buf, stderr_buf
        )
        
        self.assertIn("x = 1", filtered_code)
        self.assertIn("y = 2", filtered_code)
        self.assertIn("print(x + y)", filtered_code)
        self.assertNotIn("!pip", filtered_code)

    def test_handle_pip_install_with_parameters(self):
        code = "!pip install --upgrade pip\nprint('done')"
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        
        filtered_code = _handle_shell_commands(
            code, self.workdir, stdout_buf, stderr_buf
        )
        
        self.assertNotIn("!pip", filtered_code)
        self.assertIn("print('done')", filtered_code)

    def test_wait_for_status_returns_immediately_if_input_required_already_set(self):
        namespace = {
            "__builtins__": {
                name: getattr(builtins, name)
                for name in dir(builtins)
            }
        }
        session = SimpleNamespace(namespace=namespace, workdir=self.workdir, python_exec=None)
        run = start_interactive_run(
            session=session,
            code="name = input('Hello: ')\nprint(name)",
        )

        deadline = time.monotonic() + 2.0
        while run.status != "input_required" and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(run.status, "input_required")

        done = threading.Event()
        result = {}

        def waiter():
            result["status"] = run.wait_for_status()
            done.set()

        thread = threading.Thread(target=waiter, daemon=True)
        thread.start()
        self.assertTrue(
            done.wait(0.5),
            "wait_for_status() blocked despite terminal status already being available",
        )
        self.assertEqual(result.get("status"), "input_required")

        run.abort_input()
        run._thread.join(timeout=2.0)
        self.assertFalse(run._thread.is_alive())
