from __future__ import annotations

import ast
import base64
import io
import json
import os
import subprocess
import sys
import time
import traceback
import uuid
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Dict, Iterable
from uuid import uuid4
import logging

from .vm_models import VirtualMachine

_AGENT_CACHE: Dict[str, VmAgent] = {}
_INTERACTIVE_RUNS: Dict[str, "InteractiveRun"] = {}
logger = logging.getLogger(__name__)


def _handle_shell_commands(code: str, workdir: Path, stdout_buffer: io.StringIO, stderr_buffer: io.StringIO, python_exec: Path | None = None) -> str:
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
                    cwd=str(workdir),
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



class VmAgent(ABC):
    """Executes code within a VM and returns stdout/stderr/errors."""

    @abstractmethod
    def exec_code(self, code: str) -> Dict[str, object]:
        ...

    def exec_code_stream(self, code: str, *, stdout_path: Path, stderr_path: Path) -> Dict[str, object]:
        """Execute code while streaming stdout/stderr into files."""
        return self.exec_code(code)

    def shutdown(self) -> None:
        """Optional hook when session resets."""
        return


class _StreamingBuffer(io.TextIOBase):
    def __init__(self, path: Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._buffer = io.StringIO()
        self._file = self._path.open("a", encoding="utf-8")

    def write(self, s: str) -> int:  # type: ignore[override]
        text = "" if s is None else str(s)
        self._buffer.write(text)
        self._file.write(text)
        self._file.flush()
        return len(text)

    def flush(self) -> None:
        try:
            self._file.flush()
        except Exception as exc:
            logger.debug("Failed to flush streaming buffer %s: %s", self._path, exc)

    def getvalue(self) -> str:
        return self._buffer.getvalue()

    def isatty(self) -> bool:  # pragma: no cover - defensive
        return False

    def close(self) -> None:  # type: ignore[override]
        try:
            self._file.close()
        except Exception as exc:
            logger.debug("Failed to close streaming buffer %s: %s", self._path, exc)
        finally:
            super().close()


class _InteractiveStdin(io.TextIOBase):
    def __init__(self, run: "InteractiveRun") -> None:
        self._run = run

    @property
    def closed(self) -> bool:  # type: ignore[override]
        return self._run.stdin_closed

    def readline(self, size: int = -1) -> str:  # type: ignore[override]
        line = self._run._readline()
        if size is not None and size >= 0:
            return line[:size]
        return line

    def read(self, size: int = -1) -> str:  # type: ignore[override]
        raise RuntimeError("sys.stdin.read() is not supported in notebooks")

    def __iter__(self):
        return self

    def __next__(self) -> str:
        raise RuntimeError("iterating over sys.stdin is not supported in notebooks")


def _fileinput_blocked(*_args, **_kwargs):
    raise RuntimeError("fileinput.input() is not supported in notebooks")


class InteractiveRun:
    def __init__(
        self,
        *,
        run_id: str,
        code: str,
        session,
        stdout_buffer: io.StringIO | _StreamingBuffer,
        stderr_buffer: io.StringIO | _StreamingBuffer,
    ) -> None:
        self.run_id = run_id
        self.code = code
        self.session = session
        self.stdout_buffer = stdout_buffer
        self.stderr_buffer = stderr_buffer
        self.error: str | None = None
        self.outputs: list[dict[str, object]] = []
        self.artifacts: list[dict[str, str]] = []
        self.prompt: str | None = None
        self.status: str = "running"
        self._input_buffer: list[str] = []
        self._stdin_eof = False
        self._stdin_closed = False
        self._status_seq = 0
        self._condition = threading.Condition()
        self._thread = threading.Thread(target=self._execute, daemon=True)

    @property
    def stdin_closed(self) -> bool:
        return self._stdin_closed

    def start(self) -> None:
        _INTERACTIVE_RUNS[self.run_id] = self
        self._thread.start()

    def _set_status(self, status: str, *, prompt: str | None = None) -> None:
        with self._condition:
            self.status = status
            self.prompt = prompt
            self._status_seq += 1
            self._condition.notify_all()

    @property
    def status_seq(self) -> int:
        with self._condition:
            return self._status_seq

    def wait_for_status(self, since_seq: int | None = None) -> str:
        with self._condition:
            expected_seq = self._status_seq if since_seq is None else since_seq
            while True:
                if self.status in {"input_required", "success", "error"} and self._status_seq != expected_seq:
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

    def _input(self, prompt: str | None = None) -> str:
        prompt_text = "" if prompt is None else str(prompt)
        if prompt_text:
            self._write_stdout(prompt_text)
        self._set_status("input_required", prompt=prompt_text)
        self.wait_for_input()
        line = sys.stdin.readline()
        self._set_status("running", prompt=None)
        return line.rstrip("\n")

    def wait_for_input(self) -> None:
        with self._condition:
            while not self._input_buffer and not self._stdin_eof:
                self._condition.wait()

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

    def _execute(self) -> None:
        namespace = self.session.namespace

        def push_output(item: dict[str, object]) -> None:
            if item:
                self.outputs.append(item)

        def register_artifact(item: dict[str, object]) -> None:
            path = item.get("path")
            if not path:
                return
            name = item.get("name") or path
            self.artifacts.append({"name": str(name), "path": str(path)})

        def display(*values: object) -> None:
            if not values:
                return
            for value in values:
                item = _convert_display_value(value, session=self.session)
                if item:
                    push_output(item)
                    register_artifact(item)

        namespace.setdefault("display", display)
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
                fileinput.input = _fileinput_blocked

            sys.stdin = _InteractiveStdin(self)
            original_input = namespace.get("__builtins__", {}).get("input")
            if isinstance(namespace.get("__builtins__"), dict):
                namespace["__builtins__"]["input"] = self._input

            with _workspace_cwd(self.session.workdir), redirect_stdout(self.stdout_buffer), redirect_stderr(self.stderr_buffer):
                try:
                    _configure_pandas_display(namespace)
                    _configure_matplotlib_defaults(namespace)
                    _configure_plotly_defaults(namespace, display)
                    code = _handle_shell_commands(self.code, self.session.workdir, self.stdout_buffer, self.stderr_buffer, self.session.python_exec)
                    if code.strip():
                        _execute_with_optional_displayhook(code, namespace, display)
                except Exception:
                    self.error = traceback.format_exc()
                else:
                    for item in _capture_matplotlib_figures(self.session):
                        push_output(item)
                        register_artifact(item)
        finally:
            sys.stdin = original_stdin
            if isinstance(namespace.get("__builtins__"), dict):
                if original_input is None:
                    namespace["__builtins__"].pop("input", None)
                else:
                    namespace["__builtins__"]["input"] = original_input
            if original_fileinput is not None:
                try:
                    import fileinput
                except Exception:
                    pass
                else:
                    fileinput.input = original_fileinput
            for buffer in (self.stdout_buffer, self.stderr_buffer):
                if isinstance(buffer, _StreamingBuffer):
                    buffer.close()

        if self.error:
            self._set_status("error", prompt=None)
        else:
            self._set_status("success", prompt=None)
        _remove_interactive_run(self.run_id)

    def to_payload(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "prompt": self.prompt,
            "run_id": self.run_id,
            "stdout": self.stdout_buffer.getvalue(),
            "stderr": self.stderr_buffer.getvalue(),
            "error": self.error,
            "variables": _snapshot_variables(self.session.namespace),
            "outputs": self.outputs,
            "artifacts": self.artifacts,
        }


def _get_interactive_run(run_id: str) -> InteractiveRun | None:
    return _INTERACTIVE_RUNS.get(run_id)


def _remove_interactive_run(run_id: str) -> None:
    _INTERACTIVE_RUNS.pop(run_id, None)


def get_interactive_run(run_id: str) -> InteractiveRun | None:
    return _get_interactive_run(run_id)


def start_interactive_run(
    *,
    session,
    code: str,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    run_id: str | None = None,
) -> InteractiveRun:
    if stdout_path is not None:
        stdout_buffer: io.StringIO | _StreamingBuffer = _StreamingBuffer(stdout_path)
    else:
        stdout_buffer = io.StringIO()
    if stderr_path is not None:
        stderr_buffer: io.StringIO | _StreamingBuffer = _StreamingBuffer(stderr_path)
    else:
        stderr_buffer = io.StringIO()
    run = InteractiveRun(
        run_id=run_id or uuid.uuid4().hex,
        code=code,
        session=session,
        stdout_buffer=stdout_buffer,
        stderr_buffer=stderr_buffer,
    )
    run.start()
    return run


def provide_interactive_input(run_id: str, text: str | None, *, stdin_eof: bool = False) -> InteractiveRun | None:
    run = _get_interactive_run(run_id)
    if run is None:
        return None
    run.provide_input(text, stdin_eof=stdin_eof)
    return run


class LocalVmAgent(VmAgent):
    """Legacy in-process executor for backwards compatibility."""

    def __init__(self, session):
        self.session = session

    def exec_code(self, code: str) -> Dict[str, object]:
        return self._exec_code_with_buffers(code)

    def exec_code_stream(self, code: str, *, stdout_path: Path, stderr_path: Path) -> Dict[str, object]:
        stdout_buffer = _StreamingBuffer(stdout_path)
        stderr_buffer = _StreamingBuffer(stderr_path)
        try:
            return self._exec_code_with_buffers(code, stdout_buffer, stderr_buffer)
        finally:
            stdout_buffer.close()
            stderr_buffer.close()

    def _exec_code_with_buffers(
        self,
        code: str,
        stdout_buffer: io.StringIO | _StreamingBuffer | None = None,
        stderr_buffer: io.StringIO | _StreamingBuffer | None = None,
    ) -> Dict[str, object]:
        namespace = self.session.namespace
        stdout_buffer = stdout_buffer or io.StringIO()
        stderr_buffer = stderr_buffer or io.StringIO()
        error = None
        outputs: list[dict[str, object]] = []
        artifacts: list[dict[str, str]] = []

        def push_output(item: dict[str, object]) -> None:
            if item:
                outputs.append(item)

        def register_artifact(item: dict[str, object]) -> None:
            path = item.get("path")
            if not path:
                return
            name = item.get("name") or path
            artifacts.append({"name": str(name), "path": str(path)})

        def display(*values: object) -> None:
            if not values:
                return
            for value in values:
                item = _convert_display_value(value, session=self.session)
                if item:
                    push_output(item)
                    register_artifact(item)

        namespace.setdefault("display", display)
        with _workspace_cwd(self.session.workdir), redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            try:
                _configure_pandas_display(namespace)
                _configure_matplotlib_defaults(namespace)
                _configure_plotly_defaults(namespace, display)
                code = _handle_shell_commands(code, self.session.workdir, stdout_buffer, stderr_buffer, self.session.python_exec)
                if code.strip():
                    _execute_with_optional_displayhook(code, namespace, display)
            except Exception:
                error = traceback.format_exc()
            else:
                for item in _capture_matplotlib_figures(self.session):
                    push_output(item)
                    register_artifact(item)
        return {
            "stdout": stdout_buffer.getvalue(),
            "stderr": stderr_buffer.getvalue(),
            "error": error,
            "variables": _snapshot_variables(namespace),
            "outputs": outputs,
            "artifacts": artifacts,
        }


class FilesystemVmAgent(VmAgent):
    """Communicates with the VM agent via the shared workspace directory."""

    def __init__(self, vm: VirtualMachine, *, timeout: float = 60.0):
        self.vm = vm
        self.timeout = timeout
        self.commands_dir = vm.workspace_path / ".vm_agent" / "commands"
        self.results_dir = vm.workspace_path / ".vm_agent" / "results"

    def exec_code(self, code: str) -> Dict[str, object]:
        return self._send_payload({"code": code})

    def exec_code_stream(self, code: str, *, stdout_path: Path, stderr_path: Path) -> Dict[str, object]:
        return self._send_payload(
            {
                "code": code,
                "stream": {
                    "stdout": _relative_stream_path(self.vm.workspace_path, stdout_path),
                    "stderr": _relative_stream_path(self.vm.workspace_path, stderr_path),
                },
            }
        )

    def exec_interactive_start(
        self,
        code: str,
        *,
        run_id: str,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
    ) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "action": "interactive_start",
            "code": code,
            "run_id": run_id,
        }
        if stdout_path or stderr_path:
            payload["stream"] = {
                "stdout": _relative_stream_path(self.vm.workspace_path, stdout_path) if stdout_path else None,
                "stderr": _relative_stream_path(self.vm.workspace_path, stderr_path) if stderr_path else None,
            }
        return self._send_payload(payload)

    def exec_interactive_input(
        self,
        run_id: str,
        text: str | None,
        *,
        stdin_eof: bool = False,
    ) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "action": "interactive_input",
            "run_id": run_id,
            "input": "" if text is None else str(text),
            "stdin_eof": bool(stdin_eof),
        }
        return self._send_payload(payload)

    def _send_payload(self, payload: Dict[str, object]) -> Dict[str, object]:
        command_id = uuid.uuid4().hex
        tmp_path = self.commands_dir / f"{command_id}.json.tmp"
        final_path = self.commands_dir / f"{command_id}.json"
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(json.dumps(payload), encoding="utf-8")
        tmp_path.rename(final_path)

        result_path = self.results_dir / f"{command_id}.json"
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if result_path.exists():
                try:
                    data = json.loads(result_path.read_text(encoding="utf-8"))
                    result_path.unlink(missing_ok=True)
                    return data
                except json.JSONDecodeError:
                    pass
            time.sleep(0.05)
        raise RuntimeError("VM agent timed out waiting for execution result")


def get_vm_agent(session_id: str, session) -> VmAgent:
    agent = _AGENT_CACHE.get(session_id)
    if agent is not None:
        return agent
    vm = session.vm
    if vm and vm.backend == "docker":
        agent = FilesystemVmAgent(vm)
    else:
        agent = LocalVmAgent(session)
    _AGENT_CACHE[session_id] = agent
    return agent


def _relative_stream_path(workspace: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(workspace.resolve())
        return relative.as_posix()
    except Exception:
        return path.name


def dispose_vm_agent(session_id: str) -> None:
    agent = _AGENT_CACHE.pop(session_id, None)
    if agent:
        try:
            agent.shutdown()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to shutdown VM agent %s: %s", session_id, exc)


def reset_vm_agents() -> None:
    for session_id in list(_AGENT_CACHE.keys()):
        dispose_vm_agent(session_id)
    _INTERACTIVE_RUNS.clear()


def _snapshot_variables(namespace: Dict[str, object]) -> Dict[str, str]:
    snapshot: Dict[str, str] = {}
    for key, value in namespace.items():
        if key == "__builtins__":
            continue
        if key.startswith("__") and key.endswith("__"):
            continue
        try:
            snapshot[key] = repr(value)
        except Exception:
            snapshot[key] = f"<unrepresentable {type(value).__name__}>"
    return snapshot


def _configure_pandas_display(namespace: Dict[str, object]) -> None:
    if namespace.get("_booml_pandas_configured"):
        return
    try:
        import pandas as pd
    except Exception:
        namespace["_booml_pandas_configured"] = True
        return

    def _read_int_env(name: str, default: int) -> int:
        raw = os.environ.get(name)
        if raw is None or raw == "":
            return default
        try:
            return max(1, int(raw))
        except ValueError:
            return default

    max_rows = _read_int_env("RUNTIME_DF_MAX_ROWS", 20)
    min_rows = _read_int_env("RUNTIME_DF_MIN_ROWS", 10)
    max_cols = _read_int_env("RUNTIME_DF_MAX_COLUMNS", 20)
    max_colwidth = _read_int_env("RUNTIME_DF_MAX_COLWIDTH", 100)

    pd.set_option("display.max_rows", max_rows)
    pd.set_option("display.min_rows", min_rows)
    pd.set_option("display.max_columns", max_cols)
    pd.set_option("display.max_colwidth", max_colwidth)
    pd.set_option("display.large_repr", "truncate")
    pd.set_option("display.show_dimensions", "truncate")
    namespace["_booml_pandas_configured"] = True


def _configure_matplotlib_defaults(namespace: Dict[str, object]) -> None:
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


def _configure_plotly_defaults(namespace: Dict[str, object], display) -> None:
    if namespace.get("_booml_plotly_configured"):
        return
    try:
        import plotly.graph_objects as go
    except Exception:
        namespace["_booml_plotly_configured"] = True
        return
    try:
        original_show = go.Figure.show

        def _booml_show(self, *args, **kwargs):  # noqa: ANN001 - runtime signature
            try:
                return display(self)
            except Exception:
                return original_show(self, *args, **kwargs)

        go.Figure.show = _booml_show
    except Exception:
        pass
    namespace["_booml_plotly_configured"] = True


def _execute_with_optional_displayhook(code: str, namespace: Dict[str, object], display) -> None:
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


def _convert_display_value(value: object, *, session) -> dict[str, object] | None:
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

    dataframe_payload = _try_describe_dataframe(value)
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
                logger.debug("Failed to render HTML export", exc_info=True)
        except Exception:
            logger.debug("Failed to render HTML export", exc_info=True)

    html_repr = getattr(value, "_repr_html_", None)
    if callable(html_repr):
        try:
            html = html_repr()
            if html:
                return {"type": "text/html", "data": html}
        except Exception:
            logger.debug("Failed to render HTML repr", exc_info=True)

    md_repr = getattr(value, "_repr_markdown_", None)
    if callable(md_repr):
        try:
            md = md_repr()
            if md:
                return {"type": "text/markdown", "data": md}
        except Exception:
            logger.debug("Failed to render Markdown repr", exc_info=True)

    image_payload = _try_encode_image(value, session)
    if image_payload:
        return image_payload

    return {"type": "text/plain", "data": repr(value)}


def _try_encode_image(value: object, session) -> dict[str, object] | None:
    try:
        from PIL import Image
    except Exception:
        Image = None

    if Image is not None and isinstance(value, Image.Image):
        buffer = io.BytesIO()
        value.save(buffer, format="PNG")
        return _build_image_output(buffer.getvalue(), "image/png", session=session)
    return None


def _try_describe_dataframe(value: object) -> dict[str, object] | None:
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


def _capture_matplotlib_figures(session) -> Iterable[dict[str, object]]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []

    figures = []
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
                logger.debug("Failed to close matplotlib figure", exc_info=True)
        figures.append(_build_image_output(buffer.getvalue(), "image/png", session=session))
    return figures


def _build_image_output(payload: bytes, mime_type: str, *, session) -> dict[str, object]:
    if not payload:
        return {}
    inline_limit = int(os.environ.get("RUNTIME_OUTPUT_INLINE_MAX_BYTES", "300000"))
    if len(payload) <= inline_limit:
        encoded = base64.b64encode(payload).decode("ascii")
        return {"type": mime_type, "data": encoded}
    outputs_dir = session.workdir / ".outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    ext = "png" if mime_type == "image/png" else "img"
    filename = f"output-{uuid4().hex}.{ext}"
    target = outputs_dir / filename
    target.write_bytes(payload)
    relative = target.relative_to(session.workdir)
    return {
        "type": mime_type,
        "data": None,
        "name": filename,
        "path": relative.as_posix(),
    }


@contextmanager
def _workspace_cwd(path: Path):
    original = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


__all__ = [
    "get_vm_agent",
    "dispose_vm_agent",
    "reset_vm_agents",
    "start_interactive_run",
    "provide_interactive_input",
    "get_interactive_run",
]
