from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

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

    def test_network_access_blocked_outside_helper(self) -> None:
        session_id = "sess5"
        create_session(session_id)
        code = "import socket\nsocket.create_connection(('example.com', 80))"
        result = run_code(session_id, code)
        self.assertIsNotNone(result.error)
        self.assertIn("PermissionError", result.error or "")

    def test_blocked_imports(self) -> None:
        session_id = "sess6"
        create_session(session_id)
        result = run_code(session_id, "import ctypes")
        self.assertIsNotNone(result.error)
        self.assertIn("PermissionError", result.error or "")

    def test_os_open_blocked_outside(self) -> None:
        session_id = "sess7"
        create_session(session_id)
        result = run_code(session_id, "import os\nos.open('/etc/passwd', os.O_RDONLY)")
        self.assertIsNotNone(result.error)
        self.assertIn("PermissionError", result.error or "")

    @patch("runner.services.runtime.urlopen")
    def test_download_helper_saves_file(self, mock_urlopen) -> None:
        session_id = "sess8"
        create_session(session_id)
        chunks = [b"foo", b"bar", b""]

        class DummyResponse:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc_val, exc_tb):
                return False

            def read(self_inner, *_args, **_kwargs):
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

    def test_download_helper_blocks_disallowed_extension(self) -> None:
        session_id = "sess9"
        create_session(session_id)
        result = run_code(session_id, "download_file('https://example.com/malware.exe')")
        self.assertIsNotNone(result.error)
        self.assertIn("PermissionError", result.error or "")

    def test_allowed_download_types_exposed(self) -> None:
        session_id = "sess10"
        create_session(session_id)
        result = run_code(session_id, "extensions = allowed_download_types")
        self.assertIn("extensions", result.variables)
        self.assertIn("csv", result.variables["extensions"])

    def test_open_write_disallowed_extension(self) -> None:
        session_id = "sess11"
        create_session(session_id)
        result = run_code(session_id, "open('payload.exe','w').write('oops')")
        self.assertIsNotNone(result.error)
        self.assertIn("PermissionError", result.error or "")

    def test_rename_to_disallowed_extension_blocked(self) -> None:
        session_id = "sess12"
        create_session(session_id)
        code = (
            "open('model.bin','w').write('ok')\n"
            "import os\n"
            "os.rename('model.bin', 'model.exe')\n"
        )
        result = run_code(session_id, code)
        self.assertIsNotNone(result.error)
        self.assertIn("PermissionError", result.error or "")
