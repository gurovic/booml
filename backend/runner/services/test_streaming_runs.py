from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
from unittest.mock import patch

from django.test import SimpleTestCase

from runner.services import streaming_runs
from runner.services.runtime import RuntimeExecutionResult


@dataclass
class _FakeSession:
    workdir: Path


class StreamingRunsTests(SimpleTestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.session = _FakeSession(workdir=Path(self.tmp_dir.name))
        with streaming_runs._LOCK:
            streaming_runs._RUNS.clear()

    def tearDown(self):
        with streaming_runs._LOCK:
            streaming_runs._RUNS.clear()
        self.tmp_dir.cleanup()

    def test_run_in_progress_raises(self):
        gate = threading.Event()

        def fake_run_code_stream(_session_id, _code, *, stdout_path, stderr_path):
            gate.wait(timeout=0.3)
            return RuntimeExecutionResult(
                stdout="",
                stderr="",
                error=None,
                variables={},
                outputs=[],
                artifacts=[],
            )

        with patch("runner.services.streaming_runs.get_session", return_value=self.session), patch(
            "runner.services.streaming_runs.run_code_stream",
            side_effect=fake_run_code_stream,
        ):
            run = streaming_runs.start_streaming_run(
                session_id="notebook:1",
                cell_id=1,
                notebook_id=1,
                code="print(1)",
            )
            with self.assertRaises(streaming_runs.RunInProgressError):
                streaming_runs.start_streaming_run(
                    session_id="notebook:1",
                    cell_id=2,
                    notebook_id=1,
                    code="print(2)",
                )
            gate.set()
            for _ in range(20):
                if run.status != "running":
                    break
                time.sleep(0.02)
            self.assertIn(run.status, {"finished", "error"})

    def test_stream_files_are_cleaned_after_finish(self):
        def fake_run_code_stream(_session_id, _code, *, stdout_path, stderr_path):
            stdout_path.write_text("hello", encoding="utf-8")
            stderr_path.write_text("", encoding="utf-8")
            return RuntimeExecutionResult(
                stdout="hello",
                stderr="",
                error=None,
                variables={},
                outputs=[],
                artifacts=[],
            )

        with patch("runner.services.streaming_runs.get_session", return_value=self.session), patch(
            "runner.services.streaming_runs.run_code_stream",
            side_effect=fake_run_code_stream,
        ):
            run = streaming_runs.start_streaming_run(
                session_id="notebook:1",
                cell_id=1,
                notebook_id=1,
                code="print(1)",
            )
            for _ in range(30):
                if run.status == "finished":
                    break
                time.sleep(0.02)
            self.assertEqual(run.status, "finished")
            self.assertFalse(run.stdout_path.exists())
            self.assertFalse(run.stderr_path.exists())
