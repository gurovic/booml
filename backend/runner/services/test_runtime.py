from datetime import timedelta

from django.test import SimpleTestCase
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
        _sessions.clear()

    def test_create_and_get_session(self) -> None:
        now = timezone.now()
        session = create_session("ns", now=now)

        stored = get_session("ns", touch=False)

        self.assertIs(session, stored)
        self.assertIn("__builtins__", session.namespace)
        self.assertEqual(session.created_at, now)

        newer = timezone.now()
        touched = get_session("ns", now=newer)
        self.assertIs(touched, session)
        self.assertEqual(session.updated_at, newer)

    def test_reset_session_replaces_existing(self) -> None:
        first = create_session("ns", now=timezone.now())
        later = timezone.now() + timedelta(seconds=5)

        second = reset_session("ns", now=later)

        self.assertIsNot(first, second)
        self.assertEqual(second.created_at, later)
        self.assertEqual(second.updated_at, later)
        self.assertIs(get_session("ns", touch=False), second)

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

    def test_run_code_persists_namespace(self) -> None:
        first = run_code("session", "x = 41\nprint('hello')")

        self.assertIsNone(first.error)
        self.assertEqual(first.stdout.strip(), "hello")
        self.assertEqual(first.variables["x"], "41")

        second = run_code("session", "x += 1\nprint(x)")

        self.assertIsNone(second.error)
        self.assertEqual(second.stdout.strip(), "42")
        self.assertEqual(second.variables["x"], "42")

    def test_run_code_reports_exceptions(self) -> None:
        result = run_code("error-session", "raise ValueError('boom')")

        self.assertIsNotNone(result.error)
        self.assertIn("ValueError", result.error or "")
        self.assertEqual(result.stdout, "")

        stderr_result = run_code(
            "stderr-session",
            "import sys\nprint('ok')\nprint('warn', file=sys.stderr)",
        )
        self.assertEqual(stderr_result.stdout.strip(), "ok")
        self.assertEqual(stderr_result.stderr.strip(), "warn")
