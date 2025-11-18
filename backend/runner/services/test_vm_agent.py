import io
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import TestCase

from .vm_agent import _handle_shell_commands


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
