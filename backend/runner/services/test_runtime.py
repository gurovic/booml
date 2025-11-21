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
    cleanup_expired,
    cleanup_all_sessions,
    create_session,
    get_session,
    reset_session,
    stop_session,
    run_code,
    SessionNotFoundError,
)


class RuntimeServiceTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._sandbox_tmp = TemporaryDirectory()
        self._vm_tmp = TemporaryDirectory()
        self.override = override_settings(
            RUNTIME_SANDBOX_ROOT=self._sandbox_tmp.name,
            RUNTIME_VM_ROOT=self._vm_tmp.name,
            RUNTIME_VM_BACKEND="local",
            RUNTIME_SESSION_TTL_SECONDS=10,
        )
        self.override.enable()
        vm_manager.reset_vm_manager()
        vm_agent.reset_vm_agents()
        _sessions.clear()

    def tearDown(self) -> None:
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
