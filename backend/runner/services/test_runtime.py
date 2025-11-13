from datetime import timedelta
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from runner.services.runtime import (
    DEFAULT_SESSION_TTL_SECONDS,
    _sessions,
    cleanup_expired,
    create_session,
    get_session,
    reset_session,
    run_code,
)


class RuntimeServiceTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._tmp_dir = TemporaryDirectory()
        self.override = override_settings(RUNTIME_SANDBOX_ROOT=self._tmp_dir.name)
        self.override.enable()
        _sessions.clear()

    def tearDown(self) -> None:
        _sessions.clear()
        self.override.disable()
        self._tmp_dir.cleanup()
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

    def test_cleanup_expired_removes_old_sessions(self) -> None:
        current = timezone.now()
        stale_time = current - timedelta(seconds=DEFAULT_SESSION_TTL_SECONDS + 10)

        fresh = create_session("fresh", now=current - timedelta(seconds=10))
        expired = create_session("expired", now=stale_time)

        removed = cleanup_expired(now=current)

        self.assertIn("expired", removed)
        self.assertNotIn("expired", _sessions)
        self.assertIn("fresh", _sessions)
        self.assertIs(get_session("fresh", touch=False), fresh)

    def test_run_code_operates_inside_workdir(self) -> None:
        create_session("sess")
        result = run_code("sess", "with open('result.txt','w') as fh:\n    fh.write('ok')\nvalue = 7")
        session = get_session("sess", touch=False)
        assert session is not None
        self.assertTrue((session.workdir / "result.txt").exists())
        self.assertEqual(result.variables["value"], "7")

    def test_run_code_blocks_outside_access(self) -> None:
        create_session("sess2")
        result = run_code("sess2", "open('/tmp/forbidden.txt','w').write('x')")
        self.assertIsNotNone(result.error)
        self.assertIn("PermissionError", result.error or "")

    def test_run_code_hides_real_cwd(self) -> None:
        session_id = "sess3"
        create_session(session_id)
        result = run_code(session_id, "import os\nprint(os.getcwd())")
        self.assertIn("/sandbox", (result.stdout or ""))

    def test_subprocess_blocked(self) -> None:
        session_id = "sess4"
        create_session(session_id)
        result = run_code(session_id, "import subprocess\nsubprocess.run(['python','-V'])")
        self.assertIsNotNone(result.error)
        self.assertIn("PermissionError", result.error or "")

    def test_network_access_blocked(self) -> None:
        session_id = "sess5"
        create_session(session_id)
        result = run_code(session_id, "import socket\nsocket.socket()")
        self.assertIsNotNone(result.error)
        self.assertIn("PermissionError", result.error or "")
