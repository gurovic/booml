VM_AGENT_SERVER_SOURCE = r"""#!/usr/bin/env python3
import io
import json
import os
import sys
import subprocess
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path


COMMANDS_DIR = Path(os.environ.get("BOOML_AGENT_COMMANDS", "/workspace/.vm_agent/commands"))
RESULTS_DIR = Path(os.environ.get("BOOML_AGENT_RESULTS", "/workspace/.vm_agent/results"))
LOG_FILE = Path(os.environ.get("BOOML_AGENT_LOG", "/workspace/.vm_agent/agent.log"))
STATUS_FILE = Path(os.environ.get("BOOML_AGENT_STATUS", "/workspace/.vm_agent/status.json"))
POLL_INTERVAL = float(os.environ.get("BOOML_AGENT_POLL_INTERVAL", "0.05"))


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
        if stripped.startswith('!pip install '):
            pip_cmd = stripped[1:]
            try:
                parts = pip_cmd.split()[2:]
                cmd = [sys.executable, '-m', 'pip', 'install'] + parts + ['--disable-pip-version-check']
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(workspace),
                    timeout=300,
                    env={**os.environ, 'PIP_ROOT_USER_ACTION': 'ignore'}
                )
                stdout_buffer.write(result.stdout)
                stdout_buffer.write(result.stderr)
            except Exception as e:
                stdout_buffer.write(f"Error executing {pip_cmd}: {str(e)}\n")
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
    result = execute_code(code, namespace, workspace)
    result_path = RESULTS_DIR / command_path.name
    tmp_path = result_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(result), encoding="utf-8")
    tmp_path.rename(result_path)
    command_path.unlink(missing_ok=True)


def execute_code(code: str, namespace, workspace: Path) -> dict:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    error = None

    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        try:
            code = handle_shell_commands(code, workspace, stdout_buffer, stderr_buffer)
            if code.strip():
                exec(code, namespace, namespace)
        except Exception:
            error = traceback.format_exc()

    return {
        "stdout": stdout_buffer.getvalue(),
        "stderr": stderr_buffer.getvalue(),
        "error": error,
        "variables": snapshot_namespace(namespace),
    }


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
