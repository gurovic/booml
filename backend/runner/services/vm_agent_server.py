VM_AGENT_SERVER_SOURCE = r"""#!/usr/bin/env python3
import builtins
import io
import json
import os
import queue
import sys
import subprocess
import threading
import time
import traceback
import uuid
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path


COMMANDS_DIR = Path(os.environ.get("BOOML_AGENT_COMMANDS", "/workspace/.vm_agent/commands"))
RESULTS_DIR = Path(os.environ.get("BOOML_AGENT_RESULTS", "/workspace/.vm_agent/results"))
LOG_FILE = Path(os.environ.get("BOOML_AGENT_LOG", "/workspace/.vm_agent/agent.log"))
STATUS_FILE = Path(os.environ.get("BOOML_AGENT_STATUS", "/workspace/.vm_agent/status.json"))
POLL_INTERVAL = float(os.environ.get("BOOML_AGENT_POLL_INTERVAL", "0.05"))
RUNS = {}


def format_cell_error(code: str, exc: BaseException, file_label: str) -> str:
    lines = (code or "").splitlines()
    tb = exc.__traceback__
    lineno = None
    while tb:
        if tb.tb_frame.f_code.co_filename == "<string>":
            lineno = tb.tb_lineno
        tb = tb.tb_next
    lineno = lineno or 1
    if isinstance(exc, SyntaxError):
        if exc.lineno:
            lineno = exc.lineno
        if getattr(exc, "text", None):
            text = exc.text.rstrip("\n")
            try:
                lines[lineno - 1] = text
            except Exception:
                pass
    header = [
        "---------------------------------------------------------------------------",
        f"{type(exc).__name__}                         Traceback (most recent call last)",
        f"{file_label} in <cell line: 0>()",
    ]
    start = max(1, lineno - 1)
    if start > 1 and (start - 1) <= len(lines) and lines[start - 1].strip() == "" and lineno - 2 >= 1:
        start = lineno - 2
    end = min(len(lines), lineno + 1)
    numbered = [f"{idx:>6} {lines[idx - 1]}" for idx in range(start, end + 1)]
    target_line = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
    arrow = f"{'--->':>4} {lineno} {target_line}".rstrip()
    if start <= lineno <= end:
        numbered[lineno - start] = arrow
    tail = [
        "",
        f"{type(exc).__name__}: {exc}",
    ]
    return "\n".join([*header, *numbered, *tail])


def log(message: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")


def snapshot_namespace(namespace):
    result = {}
    for key, value in namespace.items():
        if key == "__builtins__":
            continue
        if key.startswith("__") and key.endswith("__"):
            continue
        try:
            result[key] = repr(value)
        except Exception:
            result[key] = f"<unrepresentable {type(value).__name__}>"
    return result


def build_download_helper(workspace: Path):
    import urllib.request
    from urllib.parse import urlparse

    def download_file(url, *, filename=None, chunk_size=1024 * 1024, timeout=30):
        if not isinstance(url, str) or not url.strip():
            raise ValueError("URL must be a non-empty string")
        parsed = urlparse(url)
        basename = Path(parsed.path or "").name
        target_name = filename or basename or "downloaded.file"
        target_path = workspace / target_name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        size = int(chunk_size or 0)
        if size <= 0:
            size = 1024 * 1024
        with urllib.request.urlopen(url, timeout=timeout) as response, target_path.open("wb") as destination:
            while True:
                data = response.read(size)
                if not data:
                    break
                destination.write(data)
        return str(target_path.relative_to(workspace))

    download_file.__name__ = "download_file"
    return download_file


def handle_shell_commands(code: str, workspace: Path, stdout_buffer: io.StringIO, stderr_buffer: io.StringIO) -> str:
    lines = code.split('\n')
    filtered_lines = []
    
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('!'):
            shell_cmd = stripped[1:]
            try:
                result = subprocess.run(
                    shell_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=str(workspace),
                    timeout=300,
                    env={**os.environ, 'PIP_ROOT_USER_ACTION': 'ignore'}
                )
                stdout_buffer.write(result.stdout)
                if result.stderr:
                    stderr_buffer.write(result.stderr)
            except Exception as e:
                stderr_buffer.write(f"Error executing shell command '{shell_cmd}': {str(e)}\n")
        else:
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)


def process_command(command_path: Path, namespace, workspace: Path) -> None:
    try:
        payload = json.loads(command_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"Failed to read command {command_path}: {exc}")
        command_path.unlink(missing_ok=True)
        return

    code = payload.get("code", "")
    stdin = payload.get("stdin", "")
    stdin_eof = bool(payload.get("stdin_eof", False))
    run_id = payload.get("run_id")
    result = execute_code(code, namespace, workspace, stdin=stdin, stdin_eof=stdin_eof, run_id=run_id)
    result_path = RESULTS_DIR / command_path.name
    tmp_path = result_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(result), encoding="utf-8")
    tmp_path.rename(result_path)
    command_path.unlink(missing_ok=True)


class _InteractiveStdin:
    def __init__(self, run):
        self._run = run

    @property
    def closed(self):
        return self._run.closed

    def readable(self):
        return True

    def isatty(self):
        return True

    def _read_from_buffer(self):
        if not self._run._input_buffer:
            return None
        if "\n" in self._run._input_buffer:
            line, rest = self._run._input_buffer.split("\n", 1)
            self._run._input_buffer = rest
            return f"{line}\n"
        if self._run.closed:
            data = self._run._input_buffer
            self._run._input_buffer = ""
            return data
        return None

    def readline(self, _size=-1):
        while True:
            chunk = self._read_from_buffer()
            if chunk is not None:
                return chunk
            if self._run.closed:
                return ""
            self._run.wait_for_input(prompt=None)

    def read(self, _size=-1):
        raise RuntimeError("sys.stdin.read() is not supported in this notebook runner")

    def __iter__(self):
        raise RuntimeError("Iteration over sys.stdin is not supported in this notebook runner")


class InteractiveRun:
    def __init__(self, run_id, namespace, workspace, code):
        self.run_id = run_id
        self.namespace = namespace
        self.workspace = workspace
        self.code = code
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        self.error = None
        self.prompt = None
        self.status = "running"
        self.closed = False
        self._event_queue = queue.Queue()
        self._input_condition = threading.Condition()
        self._input_buffer = ""
        self._waiting_for_input = False
        self._thread = threading.Thread(target=self._execute, daemon=True)

    def start(self):
        self._thread.start()

    def wait_for_event(self, timeout=None):
        return self._event_queue.get(timeout=timeout)

    def wait_for_input(self, prompt):
        with self._input_condition:
            self.prompt = prompt
            self.status = "input_required"
            self._waiting_for_input = True
            self._event_queue.put("input_required")
            while self._waiting_for_input and not self.closed:
                self._input_condition.wait()

    def provide_input(self, text, eof=False):
        with self._input_condition:
            if eof:
                self.closed = True
            if text:
                normalized = text if text.endswith("\n") else f"{text}\n"
                self._input_buffer += normalized
            if self.prompt and not str(self.prompt).endswith("\n"):
                self._write_stdout("\n")
            self._waiting_for_input = False
            self.status = "running"
            self._input_condition.notify_all()

    def build_result(self):
        return {
            "status": self.status,
            "prompt": self.prompt,
            "run_id": self.run_id,
            "stdout": self.stdout_buffer.getvalue(),
            "stderr": self.stderr_buffer.getvalue(),
            "error": self.error,
            "variables": snapshot_namespace(self.namespace),
        }

    def _write_stdout(self, text):
        if text:
            self.stdout_buffer.write(text)

    def _execute(self):
        original_stdin = sys.stdin
        original_input = builtins.input
        try:
            sys.stdin = _InteractiveStdin(self)

            def _input(prompt=""):
                if prompt:
                    self._write_stdout(prompt)
                self.wait_for_input(prompt or "")
                line = sys.stdin.readline()
                return line.rstrip("\n")

            builtins.input = _input

            try:
                import fileinput as _fileinput

                def _blocked_fileinput(*_args, **_kwargs):
                    raise RuntimeError("fileinput.input() is not supported in this notebook runner")

                _fileinput.input = _blocked_fileinput
            except Exception:
                pass

            with redirect_stdout(self.stdout_buffer), redirect_stderr(self.stderr_buffer):
                filtered_code = handle_shell_commands(self.code, self.workspace, self.stdout_buffer, self.stderr_buffer)
                if filtered_code.strip():
                    exec(filtered_code, self.namespace, self.namespace)
        except Exception as exc:
            self.error = format_cell_error(self.code, exc, "/workspace/.vm_agent/agent_server.py")
        finally:
            builtins.input = original_input
            sys.stdin = original_stdin
            self.status = "error" if self.error else "success"
            self._event_queue.put("finished")


RUNS_LOCK = threading.Lock()


def execute_code(code: str, namespace, workspace: Path, *, stdin: str = "", stdin_eof: bool = False, run_id: str | None = None) -> dict:
    active_run = None
    if run_id:
        with RUNS_LOCK:
            active_run = RUNS.get(run_id)
    if active_run is not None:
        active_run.provide_input(stdin or "", eof=stdin_eof)
        event = active_run.wait_for_event()
        result = active_run.build_result()
        if event == "finished":
            with RUNS_LOCK:
                RUNS.pop(run_id, None)
        return result

    run = InteractiveRun(uuid.uuid4().hex, namespace, workspace, code)
    with RUNS_LOCK:
        RUNS[run.run_id] = run
    run.start()
    event = run.wait_for_event()
    result = run.build_result()
    if event == "finished":
        with RUNS_LOCK:
            RUNS.pop(run.run_id, None)
    return result


def main() -> None:
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    workspace = Path("/workspace").resolve()
    namespace = {
        "__builtins__": __builtins__,
        "__name__": "__main__",
    }
    namespace["download_file"] = build_download_helper(workspace)

    STATUS_FILE.write_text(json.dumps({"state": "ready"}), encoding="utf-8")
    log("Agent started")

    while True:
        has_work = False
        for command_file in sorted(COMMANDS_DIR.glob("*.json")):
            has_work = True
            process_command(command_file, namespace, workspace)
        if not has_work:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"Agent crashed: {exc}")
        raise
"""

__all__ = ["VM_AGENT_SERVER_SOURCE"]
