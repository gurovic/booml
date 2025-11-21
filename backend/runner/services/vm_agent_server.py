VM_AGENT_SERVER_SOURCE = r"""#!/usr/bin/env python3
import io
import json
import os
import sys
import subprocess
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr, contextmanager
from pathlib import Path
from typing import Dict, Any


COMMANDS_DIR = Path(os.environ.get("BOOML_AGENT_COMMANDS", "/workspace/.vm_agent/commands"))
RESULTS_DIR = Path(os.environ.get("BOOML_AGENT_RESULTS", "/workspace/.vm_agent/results"))
LOG_FILE = Path(os.environ.get("BOOML_AGENT_LOG", "/workspace/.vm_agent/agent.log"))
STATUS_FILE = Path(os.environ.get("BOOML_AGENT_STATUS", "/workspace/.vm_agent/status.json"))
POLL_INTERVAL = float(os.environ.get("BOOML_AGENT_POLL_INTERVAL", "0.05"))


def log(message: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")


def serialize_variables(namespace: Dict[str, Any]) -> Dict[str, Any]:
    # Serialize namespace variables for JSON-compatible output
    result: Dict[str, Any] = {}
    
    for key, value in namespace.items():
        if key == "__builtins__":
            continue
        if key.startswith("__") and key.endswith("__"):
            continue
        result[key] = _serialize_value(value, depth=0, max_depth=3)
    
    return result


def _serialize_value(value: Any, depth: int = 0, max_depth: int = 3) -> Any:
    # Recursively serialize a single value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    
    if isinstance(value, str):
        if len(value) > 10000:
            return value[:10000] + "... (truncated)"
        return value
    
    if depth >= max_depth:
        return _make_repr_object(value)
    
    if isinstance(value, (list, tuple)):
        serialized = [_serialize_value(item, depth=depth + 1, max_depth=max_depth) for item in value[:1000]]
        if len(value) > 1000:
            serialized.append(f"... (list truncated, {len(value)} items total)")
        return serialized
    
    if isinstance(value, dict):
        serialized: Dict[str, Any] = {}
        for k, v in list(value.items())[:1000]:
            if not isinstance(k, str):
                continue
            serialized[k] = _serialize_value(v, depth=depth + 1, max_depth=max_depth)
        if len(value) > 1000:
            serialized["__truncated"] = f"Dict truncated, {len(value)} items total"
        return serialized
    
    return _make_repr_object(value)


def _make_repr_object(value: Any) -> Dict[str, str]:
    # Create a repr-based object description
    try:
        repr_str = repr(value)
    except Exception:
        repr_str = f"<unrepresentable {type(value).__name__}>"
    
    if len(repr_str) > 10000:
        repr_str = repr_str[:10000] + "... (truncated)"
    
    return {
        "__repr__": repr_str,
        "__class__": f"{type(value).__module__}.{type(value).__name__}",
    }


@contextmanager
def workspace_cwd(path: Path):
    # Temporarily change working directory
    original = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


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


def transform_shell_commands(code: str, workspace: Path) -> str:
    # Transform shell commands to function calls
    lines = code.split('\n')
    filtered_lines = []
    
    for line in lines:
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        
        # Handle !pip install specially
        if stripped.startswith('!pip install '):
            pip_cmd = stripped[1:]
            parts = pip_cmd.split()[2:]
            cmd_str = json.dumps(
                f"{sys.executable} -m pip install {' '.join(parts)} --disable-pip-version-check"
            )
            filtered_lines.append(f"{indent}_run_shell_command({cmd_str})")
            continue
        
        # Handle other ! commands
        if stripped.startswith('!'):
            cmd = stripped[1:].strip()
            cmd_str = json.dumps(cmd)
            filtered_lines.append(f"{indent}_run_shell_command({cmd_str})")
            continue
        
        filtered_lines.append(line)
    
    code_out = '\n'.join(filtered_lines)
    if '_run_shell_command' in code_out:
        helper = '''
import subprocess as _subprocess_module
import os as _os_module

def _run_shell_command(cmd: str, timeout=None):
    # Execute shell command and return output
    env = _os_module.environ.copy()
    try:
        result = _subprocess_module.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(''' + repr(str(workspace)) + '''),
            timeout=timeout,
            env=env,
        )
        if result.stdout:
            print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='', file=__import__('sys').stderr)
        return result.returncode
    except _subprocess_module.TimeoutExpired:
        print(f"Command timed out after {timeout}s", file=__import__('sys').stderr)
        return 124
    except Exception as e:
        print(f"Error running command: {e}", file=__import__('sys').stderr)
        raise
'''
        code_out = helper + '\n' + code_out


def clean_ipython_output(output: str) -> str:
    import re
    
    lines = output.split('\n')
    cleaned = []
    
    for line in lines:
        match = re.match(r'^Out\[\d+\]:\s*(.*)$', line)
        if match:
            content = match.group(1).strip()
            if content:
                cleaned.append(content)
            continue
        
        cleaned.append(line)
    
    # Join and strip each part
    result = '\n'.join(cleaned).strip()
    
    # Remove consecutive empty lines (keep max one)
    while '\n\n' in result:
        result = result.replace('\n\n', '\n')
    
    return result + '\n' if result else ''


def split_statements_preserving_blocks(code: str) -> list:
    import ast
    
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [code]
    
    if not tree.body or len(tree.body) == 1:
        return [code]
    
    lines = code.split('\n')
    statements = []
    
    for stmt in tree.body:
        start_line = stmt.lineno - 1
        end_line = stmt.end_lineno
        
        if end_line is None:
            end_line = start_line + 1
        
        stmt_lines = lines[start_line:end_line]
        stmt_code = '\n'.join(stmt_lines).strip()
        
        if stmt_code:
            statements.append(stmt_code)
    
    return statements if statements else [code]


def execute_code(code: str, namespace: Dict[str, Any], workspace: Path) -> dict:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    error = None

    with workspace_cwd(workspace), redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        try:
            try:
                from IPython import InteractiveShell
                from IPython.utils.capture import capture_output
                from IPython.core.inputtransformer2 import TransformerManager
                
                shell = InteractiveShell.instance()
                
                _validate_cell_magics(code)
                
                if '_oh' not in namespace:
                    namespace['_oh'] = {}
                if '_' not in namespace:
                    namespace['_'] = None
                if '__' not in namespace:
                    namespace['__'] = None
                if '___' not in namespace:
                    namespace['___'] = None
                if '_dh' not in namespace:
                    namespace['_dh'] = []

                existing_ns = shell.user_ns
                
                for key in list(existing_ns.keys()):
                    if key.startswith('_') or key in ('get_ipython',):
                        continue
                    if key not in namespace:
                        del existing_ns[key]
                
                existing_ns.update(namespace)

                if hasattr(shell, 'displayhook'):
                    shell.displayhook._oh = existing_ns['_oh']
                    shell.displayhook.shell = shell

                try:
                    tm = TransformerManager()
                    transformed = tm.transform_cell(code)
                except Exception as e:
                    raise SyntaxError(f"IPython transformation failed: {e}")

                if transformed.strip():
                    statements = split_statements_preserving_blocks(transformed)
                    
                    accumulated_output = []
                    for stmt in statements:
                        if stmt.strip():
                            with capture_output() as cap:
                                result = shell.run_cell(stmt, store_history=True)
                            
                            stmt_output = (cap.stdout or '') + (cap.stderr or '')
                            # Strip leading/trailing whitespace from each statement's output
                            stmt_output = stmt_output.strip()
                            if stmt_output:
                                accumulated_output.append(stmt_output)
                    
                    combined_output = '\n'.join(accumulated_output)
                    stdout_buffer.write(combined_output)
                        
            except ImportError:
                code = transform_shell_commands(code, workspace)
                if code.strip():
                    exec(code, namespace, namespace)
        except Exception:
            error = traceback.format_exc()

    return {
        "stdout": clean_ipython_output(stdout_buffer.getvalue()),
        "stderr": stderr_buffer.getvalue(),
        "error": error,
        "variables": serialize_variables(namespace),
    }


def _validate_cell_magics(code: str) -> None:
    lines = code.split('\n')
    cell_magic_count = 0
    
    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        
        if stripped.startswith('%%'):
            cell_magic_count += 1
            if cell_magic_count > 1:
                raise SyntaxError(
                    "Cell contains multiple %%cell magics. "
                    "IPython/Jupyter allows only one %%cell magic per cell."
                )


def process_command(command_path: Path, namespace: Dict[str, Any], workspace: Path) -> None:
    # Process a single command file
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


def main() -> None:
    # Main agent loop
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
