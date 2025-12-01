from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from runner.services import vm_agent, vm_manager
from runner.services.runtime import (
    DEFAULT_SESSION_TTL_SECONDS,
    _sessions,
    _resolve_now,
    cleanup_expired,
    cleanup_all_sessions,
    create_session,
    get_session,
    reset_session,
    reset_execution_backend,
    stop_session,
    run_code,
    SessionNotFoundError,
)
from runner.services.vm_models import VirtualMachine, VmNetworkPolicy, VmResources, VmSpec, VirtualMachineState


class RuntimeServiceTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._sandbox_tmp = TemporaryDirectory()
        self._vm_tmp = TemporaryDirectory()
        reset_execution_backend()
        self.override = override_settings(
            RUNTIME_SANDBOX_ROOT=self._sandbox_tmp.name,
            RUNTIME_VM_ROOT=self._vm_tmp.name,
            RUNTIME_VM_BACKEND="local",
            RUNTIME_SESSION_TTL_SECONDS=10,
            RUNTIME_EXECUTION_BACKEND="legacy",
        )
        self.override.enable()
        vm_manager.reset_vm_manager()
        vm_agent.reset_vm_agents()
        _sessions.clear()

    def tearDown(self) -> None:
        reset_execution_backend()
        _sessions.clear()
        vm_agent.reset_vm_agents()
        vm_manager.reset_vm_manager()
        self.override.disable()
        self._sandbox_tmp.cleanup()
        self._vm_tmp.cleanup()
        super().tearDown()

    def test_create_and_get_session(self) -> None:
        now = timezone.now()
        session = create_session("ns", now=now)

        stored = get_session("ns", touch=False)

        self.assertIs(session, stored)
        self.assertIn("__builtins__", session.namespace)
        self.assertTrue(session.workdir.exists())
        self.assertIsNotNone(session.python_exec)
        if session.python_exec:
            self.assertTrue(session.python_exec.exists())
        self.assertEqual(session.created_at, now)
        self.assertIsNotNone(session.vm)
        if session.vm:
            self.assertTrue(session.vm.workspace_path.exists())

        newer = timezone.now()
        touched = get_session("ns", now=newer)
        self.assertIs(touched, session)
        self.assertEqual(session.updated_at, newer)

    def test_reset_session_replaces_existing(self) -> None:
        first = create_session("ns", now=timezone.now())
        later = timezone.now() + timedelta(seconds=5)
        run_code("ns", "open('old.txt','w').write('x')")
        old_path = first.workdir / "old.txt"
        self.assertTrue(old_path.exists())

        second = reset_session("ns", now=later)

        self.assertIsNot(first, second)
        self.assertEqual(second.created_at, later)
        self.assertEqual(second.updated_at, later)
        self.assertIs(get_session("ns", touch=False), second)
        self.assertFalse(old_path.exists())
        if second.python_exec:
            self.assertTrue(second.python_exec.exists())
        self.assertIsNotNone(second.vm)

    def test_reset_session_requires_existing(self) -> None:
        with self.assertRaises(SessionNotFoundError):
            reset_session("missing")

    def test_cleanup_expired_removes_old_sessions(self) -> None:
        current = timezone.now()
        stale_time = current - timedelta(seconds=DEFAULT_SESSION_TTL_SECONDS + 10)

        fresh = create_session("fresh", now=current - timedelta(seconds=10))
        expired = create_session("expired", now=stale_time)
        vm_root = Path(self._vm_tmp.name)
        expired_vm_dir = vm_root / "runner-expired"
        self.assertTrue(expired_vm_dir.exists())

        removed = cleanup_expired(now=current)

        self.assertIn("expired", removed)
        self.assertNotIn("expired", _sessions)
        self.assertIn("fresh", _sessions)
        self.assertIs(get_session("fresh", touch=False, now=current), fresh)
        self.assertFalse(expired_vm_dir.exists())

    def test_run_code_operates_inside_workdir(self) -> None:
        create_session("sess")
        result = run_code("sess", "with open('result.txt','w') as fh:\n    fh.write('ok')\nvalue = 7")
        session = get_session("sess", touch=False)
        assert session is not None
        self.assertTrue((session.workdir / "result.txt").exists())
        self.assertEqual(result.variables["value"], "7")

    def test_run_code_requires_existing_session(self) -> None:
        with self.assertRaises(SessionNotFoundError):
            run_code("missing", "print('hi')")

    def test_stop_session_removes_workspace(self) -> None:
        session = create_session("stop-me")
        workspace = session.workdir
        self.assertTrue(workspace.exists())
        removed = stop_session("stop-me")
        self.assertTrue(removed)
        self.assertFalse(workspace.exists())
        self.assertNotIn("stop-me", _sessions)

    def test_cleanup_all_sessions_purges_everything(self) -> None:
        first = create_session("keep1")
        second = create_session("keep2")
        (first.workdir / "a.txt").write_text("data")
        (second.workdir / "b.txt").write_text("data")
        self.assertGreater(len(_sessions), 0)

        cleanup_all_sessions()

        self.assertEqual(_sessions, {})
        self.assertFalse(first.workdir.exists())
        self.assertFalse(second.workdir.exists())

    def test_run_code_reports_session_cwd(self) -> None:
        session_id = "sess2"
        session = create_session(session_id)
        result = run_code(session_id, "import os\nprint(os.getcwd())")
        self.assertIn(str(session.workdir), (result.stdout or ""))

    def test_auto_cleanup_on_create(self) -> None:
        base = timezone.now()
        expired = create_session("auto-expired", now=base)
        self.assertIn("auto-expired", _sessions)

        future = base + timedelta(seconds=20)
        create_session("auto-new", now=future)

        self.assertNotIn("auto-expired", _sessions)
        self.assertFalse(expired.workdir.exists())

    def test_auto_cleanup_on_get(self) -> None:
        base = timezone.now()
        create_session("auto-expire-get", now=base)

        future = base + timedelta(seconds=20)
        # get_session should trigger cleanup before returning value
        result = get_session("auto-expire-get", now=future)
        self.assertIsNone(result)
        self.assertNotIn("auto-expire-get", _sessions)

    @patch("runner.services.runtime.urlopen")
    def test_download_helper_saves_file(self, mock_urlopen) -> None:
        session_id = "sess3"
        create_session(session_id)
        chunks = [b"foo", b"bar", b""]

        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def read(self, *_args, **_kwargs):
                return chunks.pop(0)

        mock_urlopen.return_value = DummyResponse()
        url = "https://storage.googleapis.com/models/test.bin"
        code = (
            f"path = download_file('{url}', filename='weights.bin')\n"
            "payload = open(path, 'rb').read()\n"
        )
        result = run_code(session_id, code)
        session = get_session(session_id, touch=False)
        self.assertIsNotNone(session)
        target = session.workdir / "weights.bin"
        self.assertTrue(target.exists())
        self.assertEqual(target.read_bytes(), b"foobar")
        self.assertEqual(result.variables["payload"], "b'foobar'")

    @override_settings(RUNTIME_EXECUTION_BACKEND="jupyter")
    def test_jupyter_backend_runs_code_with_files_and_variables(self) -> None:
        try:
            create_session("jpy")
        except Exception as exc:  # noqa: BLE001 - we skip on environment issues
            if "No such kernel" in str(exc) or isinstance(exc, PermissionError):
                self.skipTest(f"Jupyter kernel unavailable in test environment: {exc}")
            raise
        result = run_code("jpy", "open('note.txt','w').write('hi')\nvalue = 42\nprint('done')")
        self.assertIn("done", result.stdout)
        self.assertIsNone(result.error)
        self.assertEqual(result.variables.get("value"), "42")
        refreshed = get_session("jpy", touch=False)
        self.assertIsNotNone(refreshed)
        if refreshed:
            self.assertTrue((refreshed.workdir / "note.txt").exists())


class JupyterBackendMockTests(SimpleTestCase):
    """Exercise Jupyter backend behavior without spawning a real kernel."""

    def setUp(self) -> None:
        super().setUp()
        self._sandbox_tmp = TemporaryDirectory()
        self._vm_tmp = TemporaryDirectory()
        reset_execution_backend()
        self.override = override_settings(
            RUNTIME_SANDBOX_ROOT=self._sandbox_tmp.name,
            RUNTIME_VM_ROOT=self._vm_tmp.name,
            RUNTIME_VM_BACKEND="local",
            RUNTIME_SESSION_TTL_SECONDS=10,
            RUNTIME_EXECUTION_BACKEND="jupyter",
        )
        self.override.enable()
        vm_manager.reset_vm_manager()
        vm_agent.reset_vm_agents()
        _sessions.clear()

    def tearDown(self) -> None:
        reset_execution_backend()
        _sessions.clear()
        vm_agent.reset_vm_agents()
        vm_manager.reset_vm_manager()
        self.override.disable()
        self._sandbox_tmp.cleanup()
        self._vm_tmp.cleanup()
        super().tearDown()

    def test_pip_and_output_are_collected(self) -> None:
        with patch("runner.services.vm_agent.subprocess.run", _fake_subprocess_run), patch(
            "jupyter_client.KernelManager", _FakeKernelManager
        ):
            create_session("jpy-mock")
            result = run_code(
                "jpy-mock",
                "!pip install pandas\nopen('note.txt','w').write('hi')\nvalue = 7\nprint('done')",
            )
            self.assertIn("pip-ok", result.stdout)
            self.assertIn("done", result.stdout)
            self.assertIsNone(result.error)
            self.assertEqual(result.variables.get("value"), "7")
            refreshed = get_session("jpy-mock", touch=False)
            self.assertIsNotNone(refreshed)
            if refreshed:
                self.assertTrue((refreshed.workdir / "note.txt").exists())

    def test_kernel_error_is_returned(self) -> None:
        with patch("jupyter_client.KernelManager", _FakeKernelManager):
            create_session("jpy-error")
            result = run_code("jpy-error", "raise_error()")
            self.assertIsNotNone(result.error)
            self.assertIn("ValueError", result.error)
            self.assertEqual(result.stdout, "")


class JupyterDockerIsolationTests(SimpleTestCase):
    """Ensure Jupyter backend delegates to VM agent when VM backend is docker."""

    def setUp(self) -> None:
        super().setUp()
        self._sandbox_tmp = TemporaryDirectory()
        reset_execution_backend()
        vm_agent.reset_vm_agents()
        _sessions.clear()
        self.override = override_settings(
            RUNTIME_SANDBOX_ROOT=self._sandbox_tmp.name,
            RUNTIME_VM_BACKEND="docker",
            RUNTIME_EXECUTION_BACKEND="jupyter",
        )
        self.override.enable()

    def tearDown(self) -> None:
        reset_execution_backend()
        vm_agent.reset_vm_agents()
        _sessions.clear()
        self.override.disable()
        self._sandbox_tmp.cleanup()
        super().tearDown()

    def test_docker_vm_uses_agent(self) -> None:
        workdir = Path(self._sandbox_tmp.name) / "runner-test"
        vm = _build_fake_docker_vm(workdir)

        class DummyAgent:
            def exec_code(self, code: str) -> dict:
                (workdir / "flag.txt").write_text("inside", encoding="utf-8")
                return {"stdout": "ok\n", "stderr": "", "error": None, "variables": {"x": "1"}}

        with patch("runner.services.runtime._ensure_session_vm", return_value=vm), patch(
            "runner.services.runtime.get_vm_agent", return_value=DummyAgent()
        ):
            try:
                session = create_session("docker-sess")
            except Exception as exc:  # noqa: BLE001
                if "Operation not permitted" in str(exc) or isinstance(exc, PermissionError):
                    self.skipTest(f"Cannot start kernel in sandboxed environment: {exc}")
                raise
            self.assertEqual(session.vm.backend, "docker")
            result = run_code("docker-sess", "x = 1")
            self.assertEqual(result.stdout.strip(), "ok")
            self.assertEqual(result.variables.get("x"), "1")
            self.assertTrue((workdir / "flag.txt").exists())


def _build_fake_docker_vm(workdir: Path) -> VirtualMachine:
    workdir.mkdir(parents=True, exist_ok=True)
    spec = VmSpec(
        image="runner-vm:latest",
        resources=VmResources(cpu=2, ram_mb=2048, disk_gb=8),
        network=VmNetworkPolicy(outbound="deny", allowlist=()),
        ttl_sec=3600,
    )
    now = _resolve_now()
    return VirtualMachine(
        id="runner-fake",
        session_id="docker-sess",
        spec=spec,
        state=VirtualMachineState.RUNNING,
        workspace_path=workdir,
        created_at=now,
        updated_at=now,
        backend="docker",
        backend_data={"container": "runner-fake"},
    )


def _fake_subprocess_run(cmd, capture_output=False, text=False, cwd=None, timeout=None, env=None):
    if not isinstance(cmd, (list, tuple)):
        raise AssertionError(f"cmd should be list/tuple, got {type(cmd)}")
    if not any("pip" in str(part) for part in cmd):
        raise AssertionError(f"Expected pip command, got: {cmd}")
    class DummyResult:
        def __init__(self) -> None:
            self.stdout = "pip-ok\n"
            self.stderr = ""

    return DummyResult()


class _FakeKernelClient:
    def __init__(self, workdir: Path):
        self.workdir = Path(workdir)
        self._iopub: list[dict] = []
        self._shell: list[dict] = []
        self._msg_counter = 0

    def start_channels(self) -> None:
        return

    def wait_for_ready(self, timeout: float | None = None) -> None:
        return

    def execute(self, code: str, store_history: bool, allow_stdin: bool, stop_on_error: bool, user_expressions: dict):
        self._msg_counter += 1
        msg_id = f"msg-{self._msg_counter}"
        stdout_text = "done\n" if "print(" in code else ""
        if stdout_text:
            self._iopub.append(
                {
                    "parent_header": {"msg_id": msg_id},
                    "msg_type": "stream",
                    "content": {"name": "stdout", "text": stdout_text},
                }
            )
        if "note.txt" in code:
            target = self.workdir / "note.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("hi")
        if "raise_error" in code:
            self._iopub.append(
                {
                    "parent_header": {"msg_id": msg_id},
                    "msg_type": "error",
                    "content": {"ename": "ValueError", "evalue": "boom", "traceback": ["ValueError: boom"]},
                }
            )
        self._iopub.append({"parent_header": {"msg_id": msg_id}, "msg_type": "status", "content": {"execution_state": "idle"}})

        var_payload = {}
        if user_expressions:
            value_text = None
            if "value" in code and "=" in code:
                value_text = code.split("=")[-1].strip().split()[0]
            var_payload = {"__booml_vars": {"status": "ok", "data": {"text/plain": str({"value": value_text})}}}
        content = {"status": "ok", "user_expressions": var_payload}
        if "raise_error" in code:
            content["status"] = "error"
            content["ename"] = "ValueError"
            content["evalue"] = "boom"
            content["traceback"] = ["ValueError: boom"]
        self._shell.append({"parent_header": {"msg_id": msg_id}, "content": content})
        return msg_id

    def get_iopub_msg(self, timeout: float | None = None):
        if not self._iopub:
            raise Empty()
        return self._iopub.pop(0)

    def get_shell_msg(self, timeout: float | None = None):
        if not self._shell:
            raise Empty()
        return self._shell.pop(0)

    def stop_channels(self) -> None:
        return


class _FakeKernelManager:
    def __init__(self, *_, **__):
        self._client: _FakeKernelClient | None = None
        self.started = False
        self.cwd: Path | None = None

    def start_kernel(self, cwd: str | None = None, env: dict | None = None) -> None:
        self.started = True
        self.cwd = Path(cwd) if cwd else None
        self._client = _FakeKernelClient(self.cwd or Path("."))

    def client(self) -> _FakeKernelClient:
        assert self._client is not None
        return self._client

    def shutdown_kernel(self, now: bool = False) -> None:
        self.started = False
