from django.test import SimpleTestCase

from runner.services import vm_agent
from runner.services.vm_agent_server import VM_AGENT_SERVER_SOURCE


class TracebackFormattingTests(SimpleTestCase):
    def _format_with_vm_agent(self, code: str) -> str:
        try:
            exec(compile(code, "<cell>", "exec"), {})
        except Exception as exc:
            return vm_agent._format_exception(exc, code=code, filename="<cell>")
        raise AssertionError("Expected exception was not raised")

    def _format_with_vm_agent_server(self, code: str) -> str:
        namespace: dict[str, object] = {}
        exec(VM_AGENT_SERVER_SOURCE, namespace)
        formatter = namespace.get("_format_exception")
        if formatter is None:
            raise AssertionError("Missing _format_exception in VM_AGENT_SERVER_SOURCE")
        try:
            exec(compile(code, "<cell>", "exec"), {})
        except Exception as exc:
            return formatter(exc, code=code, filename="<cell>")
        raise AssertionError("Expected exception was not raised")

    def test_zero_division_format(self):
        code = "a = 1\nb = 0\nc = a / b\nd = 3"
        formatted = self._format_with_vm_agent(code)

        self.assertIn("---------------------------------------------------------------------------", formatted)
        self.assertIn("ZeroDivisionError", formatted)
        self.assertIn("Traceback (most recent call last)", formatted)
        self.assertIn('<cell> in <cell line: 3>()', formatted)
        self.assertIn("     2 b = 0", formatted)
        self.assertIn("---> 3 c = a / b", formatted)
        self.assertIn("     4 d = 3", formatted)
        self.assertIn("\n\nZeroDivisionError: division by zero", formatted)
        self.assertIn("ZeroDivisionError: division by zero", formatted)
        self.assertNotIn("Ошибка:", formatted)

    def test_zero_division_format_vm_agent_server(self):
        code = "a = 1\nb = 0\nc = a / b\nd = 3"
        formatted = self._format_with_vm_agent_server(code)
        self.assertIn("ZeroDivisionError", formatted)
        self.assertIn("Traceback (most recent call last)", formatted)
        self.assertIn('<cell> in <cell line: 3>()', formatted)
        self.assertIn("     2 b = 0", formatted)
        self.assertIn("---> 3 c = a / b", formatted)
        self.assertIn("     4 d = 3", formatted)
        self.assertIn("\n\nZeroDivisionError: division by zero", formatted)
        self.assertIn("ZeroDivisionError: division by zero", formatted)

    def test_syntax_error_format(self):
        code = "x = 1\nif True print('x')\ny = 2"
        try:
            exec(compile(code, "<cell>", "exec"), {})
        except SyntaxError as exc:
            formatted = vm_agent._format_exception(exc, code=code, filename="<cell>")
        else:
            raise AssertionError("Expected SyntaxError was not raised")

        self.assertIn("SyntaxError", formatted)
        self.assertIn("Traceback (most recent call last)", formatted)
        self.assertIn('<cell> in <cell line: 2>()', formatted)
        self.assertIn("     1 x = 1", formatted)
        self.assertIn("---> 2 if True print('x')", formatted)
        self.assertIn("     3 y = 2", formatted)
        self.assertIn("\n\nSyntaxError:", formatted)
        self.assertIn("SyntaxError:", formatted)
        self.assertNotIn("Ошибка:", formatted)
