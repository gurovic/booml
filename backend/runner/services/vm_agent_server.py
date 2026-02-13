VM_AGENT_SERVER_SOURCE = r"""#!/usr/bin/env python3
import ast
import base64
import io
import json
import os
import sys
import subprocess
import time
import traceback
import uuid
import threading
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path


COMMANDS_DIR = Path(os.environ.get("BOOML_AGENT_COMMANDS", "/workspace/.vm_agent/commands"))
RESULTS_DIR = Path(os.environ.get("BOOML_AGENT_RESULTS", "/workspace/.vm_agent/results"))
LOG_FILE = Path(os.environ.get("BOOML_AGENT_LOG", "/workspace/.vm_agent/agent.log"))
STATUS_FILE = Path(os.environ.get("BOOML_AGENT_STATUS", "/workspace/.vm_agent/status.json"))
POLL_INTERVAL = float(os.environ.get("BOOML_AGENT_POLL_INTERVAL", "0.05"))

_INTERACTIVE_RUNS = {}


class StreamingBuffer(io.TextIOBase):
    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._buffer = io.StringIO()
        self._file = self._path.open("a", encoding="utf-8")

    def write(self, s):  # type: ignore[override]
        text = "" if s is None else str(s)
        self._buffer.write(text)
        self._file.write(text)
        self._file.flush()
        return len(text)

    def flush(self):
        try:
            self._file.flush()
        except Exception:
            pass

    def getvalue(self):
        return self._buffer.getvalue()

    def isatty(self):
        return False

    def close(self):  # type: ignore[override]
        try:
            self._file.close()
        finally:
            super().close()


class InteractiveStdin(io.TextIOBase):
    def __init__(self, run):
        self._run = run

    @property
    def closed(self):  # type: ignore[override]
        return self._run.stdin_closed

    def readline(self, size: int = -1):  # type: ignore[override]
        line = self._run._readline()
        if size is not None and size >= 0:
            return line[:size]
        return line

    def read(self, size: int = -1):  # type: ignore[override]
        raise RuntimeError("sys.stdin.read() is not supported in notebooks")

    def __iter__(self):
        return self

    def __next__(self):
        raise RuntimeError("iterating over sys.stdin is not supported in notebooks")


def fileinput_blocked(*_args, **_kwargs):
    raise RuntimeError("fileinput.input() is not supported in notebooks")


class InteractiveRun:
    def __init__(self, *, run_id: str, code: str, namespace, workspace: Path, stdout_buffer, stderr_buffer):
        self.run_id = run_id
        self.code = code
        self.namespace = namespace
        self.workspace = workspace
        self.stdout_buffer = stdout_buffer
        self.stderr_buffer = stderr_buffer
        self.error = None
        self.outputs = []
        self.artifacts = []
        self.prompt = None
        self.status = "running"
        self._input_buffer = []
        self._stdin_eof = False
        self._stdin_closed = False
        self._status_seq = 0
        self._condition = threading.Condition()
        self._thread = threading.Thread(target=self._execute, daemon=True)

    @property
    def stdin_closed(self):
        return self._stdin_closed

    @property
    def status_seq(self):
        with self._condition:
            return self._status_seq

    def start(self):
        _INTERACTIVE_RUNS[self.run_id] = self
        self._thread.start()

    def _set_status(self, status: str, prompt: str | None = None) -> None:
        with self._condition:
            self.status = status
            self.prompt = prompt
            self._status_seq += 1
            self._condition.notify_all()

    def wait_for_status(self, since_seq: int | None = None) -> str:
        with self._condition:
            while True:
                if self.status in {"input_required", "success", "error"}:
                    if since_seq is None or self._status_seq != since_seq:
                        return self.status
                self._condition.wait()

    def _write_stdout(self, text: str) -> None:
        if text:
            self.stdout_buffer.write(text)
            try:
                self.stdout_buffer.flush()
            except Exception:
                pass

    def _readline(self) -> str:
        with self._condition:
            if not self._input_buffer and not self._stdin_eof and self.status != "input_required":
                self._set_status("input_required", prompt="")
            while not self._input_buffer and not self._stdin_eof:
                self._condition.wait()
            if self._stdin_eof:
                self._stdin_closed = True
                return ""
            value = self._input_buffer.pop(0)
            self._set_status("running", prompt=None)
            return f"{value}\n"

    def wait_for_input(self) -> None:
        with self._condition:
            timeout_s = float(os.environ.get("RUNTIME_STDIN_TIMEOUT_SECONDS", "600"))
            deadline = time.monotonic() + max(0.0, timeout_s)
            while not self._input_buffer and not self._stdin_eof:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._stdin_eof = True
                    self._stdin_closed = True
                    self._condition.notify_all()
                    return
                self._condition.wait(timeout=remaining)

    def _input(self, prompt: str | None = None) -> str:
        prompt_text = "" if prompt is None else str(prompt)
        if prompt_text:
            self._write_stdout(prompt_text)
        self._set_status("input_required", prompt=prompt_text)
        self.wait_for_input()
        line = sys.stdin.readline()
        self._set_status("running", prompt=None)
        return line.rstrip("\n")

    def provide_input(self, text: str | None, *, stdin_eof: bool = False) -> int:
        value = "" if text is None else str(text)
        with self._condition:
            if stdin_eof:
                self._stdin_eof = True
                self._stdin_closed = True
            else:
                self._input_buffer.append(value)
                self._write_stdout(f"{value}\n")
            self._condition.notify_all()
            return self._status_seq

    def abort_input(self) -> None:
        with self._condition:
            self._stdin_eof = True
            self._stdin_closed = True
            self._condition.notify_all()

    def _execute(self) -> None:
        def push_output(item: dict) -> None:
            if item:
                self.outputs.append(item)

        def register_artifact(item: dict) -> None:
            path = item.get("path")
            if not path:
                return
            name = item.get("name") or path
            self.artifacts.append({"name": str(name), "path": str(path)})

        def display(*values):
            if not values:
                return
            for value in values:
                item = convert_display_value(value, self.workspace)
                if item:
                    push_output(item)
                    register_artifact(item)

        self.namespace.setdefault("display", display)
        original_stdin = sys.stdin
        original_input = None
        original_fileinput = None
        try:
            try:
                import fileinput
            except Exception:
                fileinput = None
            else:
                original_fileinput = fileinput.input
                fileinput.input = fileinput_blocked

            sys.stdin = InteractiveStdin(self)
            builtins_dict = self.namespace.get("__builtins__")
            if isinstance(builtins_dict, dict):
                original_input = builtins_dict.get("input")
                builtins_dict["input"] = self._input

            with redirect_stdout(self.stdout_buffer), redirect_stderr(self.stderr_buffer):
                try:
                    configure_plotly_defaults(self.namespace, display)
                    configure_matplotlib_defaults(self.namespace)
                    configure_pandas_display(self.namespace)
                    code = handle_shell_commands(self.code, self.workspace, self.stdout_buffer, self.stderr_buffer)
                    if code.strip():
                        execute_with_optional_displayhook(code, self.namespace, display)
                except Exception:
                    self.error = traceback.format_exc()
                else:
                    for item in capture_matplotlib_figures(self.workspace):
                        push_output(item)
                        register_artifact(item)
        finally:
            sys.stdin = original_stdin
            builtins_dict = self.namespace.get("__builtins__")
            if isinstance(builtins_dict, dict):
                if original_input is None:
                    builtins_dict.pop("input", None)
                else:
                    builtins_dict["input"] = original_input
            if original_fileinput is not None:
                try:
                    import fileinput
                except Exception:
                    pass
                else:
                    fileinput.input = original_fileinput
            for buffer in (self.stdout_buffer, self.stderr_buffer):
                if isinstance(buffer, StreamingBuffer):
                    buffer.close()

        if self.error:
            self._set_status("error", prompt=None)
        else:
            self._set_status("success", prompt=None)
        _INTERACTIVE_RUNS.pop(self.run_id, None)

    def to_payload(self) -> dict:
        return {
            "status": self.status,
            "prompt": self.prompt,
            "run_id": self.run_id,
            "stdout": self.stdout_buffer.getvalue(),
            "stderr": self.stderr_buffer.getvalue(),
            "error": self.error,
            "variables": snapshot_namespace(self.namespace),
            "outputs": self.outputs,
            "artifacts": self.artifacts,
        }


def open_stream_buffer(workspace: Path, raw_path: str | None):
    if not raw_path:
        return None
    try:
        target = (workspace / raw_path).resolve()
        target.relative_to(workspace.resolve())
    except Exception:
        return None
    return StreamingBuffer(target)


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


def execute_with_optional_displayhook(code: str, namespace, display) -> None:
    try:
        parsed = ast.parse(code, mode="exec")
    except SyntaxError:
        exec(code, namespace, namespace)
        return

    if not parsed.body:
        return

    has_future_import = any(
        isinstance(node, ast.ImportFrom) and node.module == "__future__"
        for node in parsed.body
    )
    last_node = parsed.body[-1]
    if has_future_import or not isinstance(last_node, ast.Expr):
        exec(compile(parsed, "<cell>", "exec"), namespace, namespace)
        return

    body = parsed.body[:-1]
    if body:
        exec(compile(ast.Module(body=body, type_ignores=[]), "<cell>", "exec"), namespace, namespace)

    expr = ast.Expression(last_node.value)
    result = eval(compile(expr, "<cell>", "eval"), namespace, namespace)
    if result is not None:
        display(result)


def convert_display_value(value, workspace: Path) -> dict | None:
    if value is None:
        return None

    if isinstance(value, dict) and value.get("type"):
        return {
            "type": str(value.get("type")),
            "data": value.get("data"),
            "metadata": value.get("metadata"),
            "name": value.get("name"),
            "path": value.get("path"),
        }

    dataframe_payload = try_describe_dataframe(value)
    if dataframe_payload:
        return dataframe_payload

    html_export = getattr(value, "to_html", None)
    if callable(html_export):
        try:
            html = html_export(full_html=False, include_plotlyjs="cdn")
            if html:
                return {"type": "text/html", "data": html}
        except TypeError:
            try:
                html = html_export()
                if html:
                    return {"type": "text/html", "data": html}
            except Exception:
                pass
        except Exception:
            pass

    html_repr = getattr(value, "_repr_html_", None)
    if callable(html_repr):
        try:
            html = html_repr()
            if html:
                return {"type": "text/html", "data": html}
        except Exception:
            pass

    md_repr = getattr(value, "_repr_markdown_", None)
    if callable(md_repr):
        try:
            md = md_repr()
            if md:
                return {"type": "text/markdown", "data": md}
        except Exception:
            pass

    image_payload = try_encode_image(value, workspace)
    if image_payload:
        return image_payload

    return {"type": "text/plain", "data": repr(value)}


def try_encode_image(value, workspace: Path) -> dict | None:
    try:
        from PIL import Image
    except Exception:
        Image = None

    if Image is not None and isinstance(value, Image.Image):
        buffer = io.BytesIO()
        value.save(buffer, format="PNG")
        return build_image_output(buffer.getvalue(), "image/png", workspace)
    return None


def capture_matplotlib_figures(workspace: Path) -> list[dict]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []

    outputs = []
    try:
        fig_nums = plt.get_fignums()
    except Exception:
        return []

    for num in fig_nums:
        try:
            fig = plt.figure(num)
        except Exception:
            continue
        buffer = io.BytesIO()
        try:
            fig.savefig(buffer, format="png", bbox_inches="tight")
        except Exception:
            continue
        finally:
            try:
                plt.close(fig)
            except Exception:
                pass
        outputs.append(build_image_output(buffer.getvalue(), "image/png", workspace))
    return outputs


def build_image_output(payload: bytes, mime_type: str, workspace: Path) -> dict:
    if not payload:
        return {}
    inline_limit = int(os.environ.get("RUNTIME_OUTPUT_INLINE_MAX_BYTES", "300000"))
    if len(payload) <= inline_limit:
        encoded = base64.b64encode(payload).decode("ascii")
        return {"type": mime_type, "data": encoded}
    outputs_dir = workspace / ".outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    ext = "png" if mime_type == "image/png" else "img"
    filename = f"output-{uuid.uuid4().hex}.{ext}"
    target = outputs_dir / filename
    target.write_bytes(payload)
    relative = target.relative_to(workspace)
    return {
        "type": mime_type,
        "data": None,
        "name": filename,
        "path": relative.as_posix(),
    }


def process_command(command_path: Path, namespace, workspace: Path) -> None:
    try:
        payload = json.loads(command_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"Failed to read command {command_path}: {exc}")
        command_path.unlink(missing_ok=True)
        return

    action = payload.get("action") or "run"
    code = payload.get("code", "")
    stream = payload.get("stream") or {}
    if action == "interactive_start":
        run_id = payload.get("run_id") or None
        result = start_interactive(code, namespace, workspace, stream=stream, run_id=run_id)
    elif action == "interactive_input":
        run_id = payload.get("run_id") or ""
        text = payload.get("input")
        stdin_eof = bool(payload.get("stdin_eof"))
        result = provide_interactive_input(run_id, text, stdin_eof=stdin_eof)
    else:
        result = execute_code(code, namespace, workspace, stream=stream)
    result_path = RESULTS_DIR / command_path.name
    tmp_path = result_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(result), encoding="utf-8")
    tmp_path.rename(result_path)
    command_path.unlink(missing_ok=True)


def execute_code(code: str, namespace, workspace: Path, *, stream: dict | None = None) -> dict:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    stdout_stream = None
    stderr_stream = None
    if stream:
        stdout_stream = open_stream_buffer(workspace, stream.get("stdout"))
        stderr_stream = open_stream_buffer(workspace, stream.get("stderr"))
        if stdout_stream:
            stdout_buffer = stdout_stream
        if stderr_stream:
            stderr_buffer = stderr_stream
    error = None
    outputs = []
    artifacts = []

    def push_output(item: dict) -> None:
        if item:
            outputs.append(item)

    def register_artifact(item: dict) -> None:
        path = item.get("path")
        if not path:
            return
        name = item.get("name") or path
        artifacts.append({"name": str(name), "path": str(path)})

    def display(*values):
        if not values:
            return
        for value in values:
            item = convert_display_value(value, workspace)
            if item:
                push_output(item)
                register_artifact(item)

    try:
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            try:
                configure_plotly_defaults(namespace, display)
                configure_matplotlib_defaults(namespace)
                configure_pandas_display(namespace)
                code = handle_shell_commands(code, workspace, stdout_buffer, stderr_buffer)
                if code.strip():
                    execute_with_optional_displayhook(code, namespace, display)
            except Exception:
                error = traceback.format_exc()
            else:
                for item in capture_matplotlib_figures(workspace):
                    push_output(item)
                    register_artifact(item)
    finally:
        if stdout_stream:
            stdout_stream.close()
        if stderr_stream:
            stderr_stream.close()

    return {
        "stdout": stdout_buffer.getvalue(),
        "stderr": stderr_buffer.getvalue(),
        "error": error,
        "variables": snapshot_namespace(namespace),
        "outputs": outputs,
        "artifacts": artifacts,
    }


def start_interactive(code: str, namespace, workspace: Path, *, stream: dict | None = None, run_id: str | None = None) -> dict:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    if stream:
        stdout_stream = open_stream_buffer(workspace, stream.get("stdout"))
        stderr_stream = open_stream_buffer(workspace, stream.get("stderr"))
        if stdout_stream:
            stdout_buffer = stdout_stream
        if stderr_stream:
            stderr_buffer = stderr_stream
    run = InteractiveRun(
        run_id=run_id or uuid.uuid4().hex,
        code=code,
        namespace=namespace,
        workspace=workspace,
        stdout_buffer=stdout_buffer,
        stderr_buffer=stderr_buffer,
    )
    run.start()
    run.wait_for_status()
    return run.to_payload()


def provide_interactive_input(run_id: str, text: str | None, *, stdin_eof: bool = False) -> dict:
    run = _INTERACTIVE_RUNS.get(run_id)
    if run is None:
        return {
            "status": "error",
            "prompt": None,
            "run_id": run_id,
            "stdout": "",
            "stderr": "",
            "error": "Interactive run not found",
            "variables": {},
            "outputs": [],
            "artifacts": [],
        }
    seq = run.status_seq
    run.provide_input(text, stdin_eof=stdin_eof)
    run.wait_for_status(since_seq=seq)
    return run.to_payload()


def configure_pandas_display(namespace) -> None:
    if namespace.get("_booml_pandas_configured"):
        return
    try:
        import pandas as pd
    except Exception:
        namespace["_booml_pandas_configured"] = True
        return

    def read_int_env(name: str, default: int) -> int:
        raw = os.environ.get(name)
        if raw is None or raw == "":
            return default
        try:
            return max(1, int(raw))
        except ValueError:
            return default

    max_rows = read_int_env("RUNTIME_DF_MAX_ROWS", 20)
    min_rows = read_int_env("RUNTIME_DF_MIN_ROWS", 10)
    max_cols = read_int_env("RUNTIME_DF_MAX_COLUMNS", 20)
    max_colwidth = read_int_env("RUNTIME_DF_MAX_COLWIDTH", 100)

    pd.set_option("display.max_rows", max_rows)
    pd.set_option("display.min_rows", min_rows)
    pd.set_option("display.max_columns", max_cols)
    pd.set_option("display.max_colwidth", max_colwidth)
    pd.set_option("display.large_repr", "truncate")
    pd.set_option("display.show_dimensions", "truncate")
    namespace["_booml_pandas_configured"] = True


def configure_plotly_defaults(namespace, display) -> None:
    if namespace.get("_booml_plotly_configured"):
        return
    try:
        import plotly.graph_objects as go
    except Exception:
        namespace["_booml_plotly_configured"] = True
        return
    try:
        original_show = go.Figure.show

        def _booml_show(self, *args, **kwargs):
            try:
                return display(self)
            except Exception:
                return original_show(self, *args, **kwargs)

        go.Figure.show = _booml_show
    except Exception:
        pass
    namespace["_booml_plotly_configured"] = True


def configure_matplotlib_defaults(namespace) -> None:
    if namespace.get("_booml_matplotlib_configured"):
        return
    try:
        import matplotlib as mpl
    except Exception:
        namespace["_booml_matplotlib_configured"] = True
        return
    try:
        mpl.rcParams["figure.dpi"] = 120
        mpl.rcParams["savefig.dpi"] = 120
        mpl.rcParams["figure.figsize"] = (6, 4)
        mpl.rcParams["axes.grid"] = True
        mpl.rcParams["grid.alpha"] = 0.2
        mpl.rcParams["savefig.bbox"] = "tight"
    except Exception:
        pass
    try:
        import matplotlib.pyplot as plt
        try:
            plt.style.use("seaborn-v0_8-whitegrid")
        except Exception:
            plt.style.use("ggplot")
    except Exception:
        pass
    namespace["_booml_matplotlib_configured"] = True


def try_describe_dataframe(value) -> dict | None:
    try:
        import pandas as pd
    except Exception:
        return None

    if not isinstance(value, pd.DataFrame):
        return None

    try:
        html = value.to_html()
    except Exception:
        return None

    try:
        nulls_total = int(value.isna().sum().sum())
    except Exception:
        nulls_total = None
    try:
        memory_bytes = int(value.memory_usage(deep=True).sum())
    except Exception:
        memory_bytes = None

    columns_preview = []
    truncated = False
    preview_limit = 12
    try:
        for idx, (name, dtype) in enumerate(value.dtypes.items()):
            if idx >= preview_limit:
                truncated = True
                break
            col = value[name]
            try:
                non_null = int(col.notna().sum())
                nulls = int(col.isna().sum())
            except Exception:
                non_null = None
                nulls = None
            columns_preview.append(
                {
                    "name": str(name),
                    "dtype": str(dtype),
                    "non_null": non_null,
                    "nulls": nulls,
                }
            )
    except Exception:
        columns_preview = []

    dtype_counts = None
    try:
        dtype_counts = value.dtypes.astype(str).value_counts().to_dict()
    except Exception:
        dtype_counts = None

    metadata = {
        "rows": int(value.shape[0]),
        "columns": int(value.shape[1]),
        "nulls_total": nulls_total,
        "memory_bytes": memory_bytes,
        "dtype_counts": dtype_counts,
        "columns_preview": columns_preview,
        "columns_truncated": truncated,
    }
    return {"type": "text/html", "data": html, "metadata": metadata}


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
