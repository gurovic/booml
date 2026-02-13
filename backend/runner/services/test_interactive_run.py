import io
import time
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.test import SimpleTestCase

from runner.services import vm_agent
from runner.services.vm_agent_server import VM_AGENT_SERVER_SOURCE


class InteractiveRunWaitForStatusTests(SimpleTestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        workdir = Path(self.tmpdir.name)
        self.session = SimpleNamespace(namespace={}, workdir=workdir, python_exec=None)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _make_vm_agent_run(self) -> vm_agent.InteractiveRun:
        return vm_agent.InteractiveRun(
            run_id="run-agent",
            code="",
            session=self.session,
            stdout_buffer=io.StringIO(),
            stderr_buffer=io.StringIO(),
        )

    def _make_vm_agent_server_run(self):
        namespace: dict[str, object] = {}
        exec(VM_AGENT_SERVER_SOURCE, namespace)
        run_cls = namespace.get("InteractiveRun")
        if run_cls is None:
            raise AssertionError("InteractiveRun is missing in VM_AGENT_SERVER_SOURCE")
        return run_cls(
            run_id="run-server",
            code="",
            namespace={},
            workspace=self.session.workdir,
            stdout_buffer=io.StringIO(),
            stderr_buffer=io.StringIO(),
        )

    def _assert_returns_immediately(self, run, expected: str) -> None:
        start = time.monotonic()
        status = run.wait_for_status()
        elapsed = time.monotonic() - start
        self.assertEqual(status, expected)
        self.assertLess(elapsed, 0.1)

    def _assert_since_seq_returns(self, run, expected: str) -> None:
        seq = run.status_seq
        run._set_status(expected, prompt=None)
        status = run.wait_for_status(since_seq=seq)
        self.assertEqual(status, expected)

    def test_vm_agent_wait_for_status_returns_when_already_input_required(self):
        run = self._make_vm_agent_run()
        run._set_status("input_required", prompt="")
        self._assert_returns_immediately(run, "input_required")

    def test_vm_agent_wait_for_status_since_seq_returns_after_status_change(self):
        run = self._make_vm_agent_run()
        self._assert_since_seq_returns(run, "success")

    def test_vm_agent_wait_for_status_blocks_until_change(self):
        run = self._make_vm_agent_run()

        def _flip_status():
            time.sleep(0.05)
            run._set_status("success", prompt=None)

        thread = threading.Thread(target=_flip_status, daemon=True)
        thread.start()
        start = time.monotonic()
        status = run.wait_for_status()
        elapsed = time.monotonic() - start
        self.assertEqual(status, "success")
        self.assertGreaterEqual(elapsed, 0.04)

    def test_vm_agent_server_wait_for_status_returns_when_already_input_required(self):
        run = self._make_vm_agent_server_run()
        run._set_status("input_required", prompt="")
        self._assert_returns_immediately(run, "input_required")

    def test_vm_agent_server_wait_for_status_since_seq_returns_after_status_change(self):
        run = self._make_vm_agent_server_run()
        self._assert_since_seq_returns(run, "success")

    def test_vm_agent_server_wait_for_status_blocks_until_change(self):
        run = self._make_vm_agent_server_run()

        def _flip_status():
            time.sleep(0.05)
            run._set_status("success", prompt=None)

        thread = threading.Thread(target=_flip_status, daemon=True)
        thread.start()
        start = time.monotonic()
        status = run.wait_for_status()
        elapsed = time.monotonic() - start
        self.assertEqual(status, "success")
        self.assertGreaterEqual(elapsed, 0.04)
