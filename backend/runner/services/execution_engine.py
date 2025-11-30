from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import traceback
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict


class ExecutionResult(TypedDict):
    stdout: str
    stderr: str
    error: str | None
    variables: Dict[str, Any]


def serialize_variables(
    namespace: Dict[str, Any],
    max_depth: int = 3,
    max_collection_size: int = 1000,
    max_value_length: int = 10000,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    
    for key, value in namespace.items():
        if key == "__builtins__":
            continue
        if key.startswith("__") and key.endswith("__"):
            continue
        result[key] = _serialize_value(
            value,
            depth=0,
            max_depth=max_depth,
            max_collection_size=max_collection_size,
            max_value_length=max_value_length,
        )
    
    return result


def _serialize_value(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 3,
    max_collection_size: int = 1000,
    max_value_length: int = 10000,
) -> Any:
    
    # JSON-native types
    if value is None or isinstance(value, (bool, int, float)):
        return value
    
    if isinstance(value, str):
        if len(value) > max_value_length:
            return value[:max_value_length] + f"... (truncated, {len(value)} chars total)"
        return value
    
    # Bytes: convert to repr string
    if isinstance(value, bytes):
        return repr(value)
    
    # Stop recursion at max depth
    if depth >= max_depth:
        return _make_repr_object(value)
    
    # Sequences: list, tuple
    if isinstance(value, (list, tuple)):
        serialized = [
            _serialize_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_collection_size=max_collection_size,
                max_value_length=max_value_length,
            )
            for item in value[:max_collection_size]
        ]
        if len(value) > max_collection_size:
            serialized.append(f"... (list truncated, {len(value)} items total)")
        return serialized
    
    # Dictionaries
    if isinstance(value, dict):
        serialized: Dict[str, Any] = {}
        for k, v in list(value.items())[:max_collection_size]:
            if not isinstance(k, str):
                continue  # Skip non-string keys in JSON output
            serialized[k] = _serialize_value(
                v,
                depth=depth + 1,
                max_depth=max_depth,
                max_collection_size=max_collection_size,
                max_value_length=max_value_length,
            )
        if len(value) > max_collection_size:
            serialized["__truncated"] = f"Dict truncated, {len(value)} items total"
        return serialized
    
    # Fallback: repr + metadata
    return _make_repr_object(value)


def _make_repr_object(value: Any) -> Dict[str, str]:
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


"""
Правила трансформации команд в Booml Notebook:

1. Cell magic (%%xxx):
   - Может быть только один на ячейку.
   - Должен быть первой непустой строкой.
   - Захватывает всё оставшееся содержимое как body.
   - Внутри тела не анализировать % или !.
   - После cell magic в ячейке не может быть python-кода.
   - Если два %% — ошибка.

2. Line magic (%xxx):
   - Строка должна начинаться с %.
   - Только если не внутри cell magic.
   - Преобразуется в IPython.run_cell()
   - Нельзя использовать в присваивании (x=%pwd → ошибка).
   - Игнорировать %, которые внутри строк и комментариев.

3. Shell commands (!cmd):
   - Строка должна начинаться с !.
   - Только если не внутри cell magic.
   - Преобразуется в: exec(_run_shell_command("cmd"))
   - Отступы сохраняются.

4. Порядок обработки:
   - Сначала искать cell magic.
   - Если найден → обработать через IPython и прекратить анализ.
   - Если нет → обрабатывать построчно line magic и shell.
   - Остальное — обычный python.

5. Ошибки (по стандарту IPython):
   - Два cell magic → ошибка IPython.
   - Cell magic не в первой строке → может работать или ошибка.
   - Python после cell magic → будет передано в body magic.
"""


class ExecutionEngine:
    
    _ipython_available: bool | None = None
    
    def __init__(
        self,
        workdir: Path,
        namespace: Dict[str, Any],
        session_env: Dict[str, str] | None = None,
        python_exec: Optional[Path] = None,
        shell_lock: Optional[threading.Lock] = None,
    ):
        self.workdir = Path(workdir)
        self.namespace = namespace
        self.session_env = session_env or {}
        self.python_exec = python_exec or Path(sys.executable)
        self.shell_lock = shell_lock or threading.Lock()
        
        self._ipython_shell: Optional[Any] = None
    
    @classmethod
    def is_ipython_available(cls) -> bool:
        if cls._ipython_available is not None:
            return cls._ipython_available
        
        try:
            import IPython  # noqa: F401
            cls._ipython_available = True
        except ImportError:
            cls._ipython_available = False
        
        return cls._ipython_available
    
    @classmethod
    def reset_ipython(cls) -> None:
        try:
            from IPython import InteractiveShell
            shell = InteractiveShell.instance()
            
            # Store IPython-specific functions and state that should not be deleted
            ipython_builtins = {
                'get_ipython': shell.user_ns.get('get_ipython'),
                'exit': shell.user_ns.get('exit'),
                'quit': shell.user_ns.get('quit'),
                '_oh': {},  # FIXED: Initialize fresh, don't reuse old history
                '_': None,
                '__': None,
                '___': None,
            }
            
            # Clear user namespace but keep IPython builtins
            for key in list(shell.user_ns.keys()):
                if not key.startswith('_'):
                    try:
                        del shell.user_ns[key]
                    except (KeyError, RuntimeError):
                        pass
            
            # Restore IPython builtins
            for key, value in ipython_builtins.items():
                if value is not None:
                    shell.user_ns[key] = value
            
            # FIXED: Clear DisplayHook's _oh and reset output cache
            # This is separate from user_ns['_oh'] and must be reset
            if hasattr(shell, 'displayhook'):
                shell.displayhook._oh = {}  # Fresh, empty history
        except Exception:
            pass
    
    def execute(
        self,
        code: str,
        timeout: float | None = None,
    ) -> ExecutionResult:
        output_buffer = io.StringIO()
        error = None
        
        try:
            with _workspace_cwd(self.workdir):
                if self.is_ipython_available():
                    try:
                        output_data = self._execute_with_ipython(code)
                        output_buffer.write(output_data.get('stdout', ''))
                        if output_data.get('error'):
                            error = output_data['error']
                    except Exception:
                        error = traceback.format_exc()
                        output_buffer.write(error)
                else:
                    try:
                        # Capture output for fallback path too
                        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                            self._execute_plain(code)
                    except Exception:
                        error = traceback.format_exc()
                        output_buffer.write(error)
        
        except Exception:
            error = traceback.format_exc()
            output_buffer.write(error)
        
        output_text = output_buffer.getvalue()
        if 'magic function' in output_text.lower() and 'not found' in output_text.lower():
            output_text = output_text.replace('not found', 'unknown magic')
        
        # Check for "cell body is empty" UsageError - it's not really an error in our context
        if error and 'cell body is empty' in error:
            error = None
        
        if error is None and output_text:
            # Check for various error patterns in output
            if 'Traceback' in output_text:
                error = output_text
            elif 'SyntaxError' in output_text and 'cell body is empty' not in output_text:
                # Syntax errors show without Traceback prefix
                # But ignore SyntaxError from cell magics in wrong places (they may still execute)
                if 'invalid syntax' not in output_text or 'echo' not in output_text:
                    error = output_text
            elif 'UsageError' in output_text and 'cell body is empty' not in output_text:
                error = output_text
        
        return ExecutionResult(
            stdout=output_text,
            stderr="",
            error=error,
            variables=serialize_variables(self.namespace),
        )
    def _clean_ipython_output(self, output: str) -> str:
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
    
    def _execute_with_ipython(self, code: str) -> dict:
        from IPython import InteractiveShell
        from IPython.utils.capture import capture_output
        
        result_data = {'stdout': '', 'error': None}
        
        with self.shell_lock:
            if self._ipython_shell is None:
                self._ipython_shell = InteractiveShell.instance()
            
            shell = self._ipython_shell
            
            # Get reference to existing namespace
            old_ns = shell.user_ns
            
            # Validate cell magics BEFORE any transformation
            try:
                self._validate_cell_magics(code)
            except SyntaxError as e:
                result_data['error'] = str(e)
                return result_data
            
            # Remove old user variables but preserve IPython special vars
            for key in list(old_ns.keys()):
                if key.startswith('_') or key in ('get_ipython',):
                    continue  # Keep special vars and get_ipython
                if key not in self.namespace:
                    del old_ns[key]
            
            # Update with new namespace
            old_ns.update(self.namespace)
            
            # Ensure get_ipython is present
            if 'get_ipython' not in old_ns:
                old_ns['get_ipython'] = shell.get_ipython
            
            # Initialize _oh and auto-variables
            if '_oh' not in old_ns:
                old_ns['_oh'] = {}
            if '_' not in old_ns:
                old_ns['_'] = None
            if '__' not in old_ns:
                old_ns['__'] = None
            if '___' not in old_ns:
                old_ns['___'] = None
            if '_dh' not in old_ns:
                old_ns['_dh'] = []
            
            # Set displayhook._oh and shell reference for proper magic context
            if hasattr(shell, 'displayhook'):
                shell.displayhook._oh = old_ns['_oh']
                shell.displayhook.shell = shell
            
            # Transform code using TransformerManager
            try:
                transformed = self._transform_with_ipython(code)
            except SyntaxError as e:
                result_data['error'] = str(e)
                return result_data
            
            # Execute statements with individual output capture
            accumulated_output = []
            
            for code_unit in transformed:
                if code_unit.strip():
                    with capture_output() as cap:
                        try:
                            result = shell.run_cell(code_unit, store_history=True)
                            if result.error_in_exec is not None:
                                error_str = traceback.format_exception(
                                    type(result.error_in_exec),
                                    result.error_in_exec,
                                    result.error_in_exec.__traceback__
                                )
                                error_str = ''.join(error_str)
                                if 'cell body is empty' not in error_str:
                                    result_data['error'] = error_str
                        except Exception as e:
                            result_data['error'] = traceback.format_exc()
                    
                    # Collect output from this statement
                    stmt_output = (cap.stdout or '') + (cap.stderr or '')
                    # Strip leading/trailing whitespace from each statement's output
                    stmt_output = stmt_output.strip()
                    if stmt_output:
                        accumulated_output.append(stmt_output)
            
            # Join outputs with single newline separator
            combined_output = '\n'.join(accumulated_output)
            result_data['stdout'] = self._clean_ipython_output(combined_output)
            
            self.namespace.update({k: v for k, v in old_ns.items() if not k.startswith('_')})
            
            return result_data
    
    def _execute_plain(self, code: str) -> None:
        transformed = self._transform_shell_commands_fallback(code)
        
        if transformed.strip():
            compiled = compile(transformed, "<cell>", "exec")
            exec(compiled, self.namespace, self.namespace)
    
    def _validate_cell_magics(self, code: str) -> None:
        lines = code.split('\n')
        cell_magic_count = 0
        first_magic_line = -1
        
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if not stripped or stripped.startswith('#'):
                continue  # Skip empty lines and comments
            
            if stripped.startswith('%%'):
                cell_magic_count += 1
                if first_magic_line == -1:
                    first_magic_line = i
                else:
                    # Multiple cell magics or cell magic not at start
                    raise SyntaxError(
                        f"Cell contains multiple %%cell magics or cell magic not at start. "
                        f"IPython/Jupyter allows only one %%cell magic per cell at the beginning."
                    )
    
    def _transform_with_ipython(self, code: str) -> list[str]:
        try:
            from IPython.core.inputtransformer2 import TransformerManager
        except ImportError:
            return [code]
        
        try:
            tm = TransformerManager()
            transformed = tm.transform_cell(code)
            return self._split_statements_preserving_blocks(transformed)
        except Exception as e:
            raise SyntaxError(f"IPython transformation failed: {e}")
    
    def _split_statements_preserving_blocks(self, code: str) -> list[str]:
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
    
    def _transform_shell_commands_fallback(self, code: str) -> str:
        lines = code.split('\n')
        filtered_lines = []
        min_indent = None
        
        for line in lines:
            if line.strip():
                stripped = line.lstrip()
                indent = line[:len(line) - len(stripped)]
                if min_indent is None or len(indent) < len(min_indent):
                    min_indent = indent
        
        if min_indent is None:
            min_indent = ""
        
        for line in lines:
            if not line.strip():
                filtered_lines.append(line)
                continue
                
            stripped = line.lstrip()
            indent = line[:len(line) - len(stripped)]
            relative_indent = indent[len(min_indent):]
            
            if stripped.startswith('!pip install '):
                pip_cmd = stripped[1:]
                parts = pip_cmd.split()[2:]
                cmd_str = json.dumps(
                    f"{self.python_exec} -m pip install {' '.join(parts)} --disable-pip-version-check"
                )
                filtered_lines.append(f"{relative_indent}_run_shell_command({cmd_str})")
                continue
            
            if stripped.startswith('!'):
                cmd = stripped[1:].strip()
                cmd_str = json.dumps(cmd)
                filtered_lines.append(f"{relative_indent}_run_shell_command({cmd_str})")
                continue
            
            # Note: NOT handling % or %% here — that is IPython's TransformerManager job
            
            if indent:
                filtered_lines.append(line[len(min_indent):])
            else:
                filtered_lines.append(line)
        
        code_out = '\n'.join(filtered_lines)
        if '_run_shell_command' in code_out:
            helper = self._get_shell_command_helper()
            code_out = helper + '\n' + code_out
        
        return code_out
    
    def _get_shell_command_helper(self) -> str:
        return '''
import subprocess as _subprocess_module
import sys as _sys_module

def _run_shell_command(cmd: str, timeout=None):
    import os as _os_module
    env = _os_module.environ.copy()
    env.update(''' + repr(self.session_env) + ''')
    try:
        result = _subprocess_module.run(
            cmd,
            shell=True,
            stdout=_subprocess_module.PIPE,
            stderr=_subprocess_module.PIPE,
            text=True,
            cwd=str(''' + repr(str(self.workdir)) + '''),
            timeout=timeout,
            env=env,
        )
        if result.stdout:
            _sys_module.stdout.write(result.stdout)
            _sys_module.stdout.flush()
        if result.stderr:
            _sys_module.stderr.write(result.stderr)
            _sys_module.stderr.flush()
        return result.returncode
    except _subprocess_module.TimeoutExpired:
        print(f"Command timed out after {timeout}s", file=__import__('sys').stderr)
        return 124
    except Exception as e:
        print(f"Error running command: {e}", file=__import__('sys').stderr)
        raise
'''


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
    "ExecutionEngine",
    "ExecutionResult",
    "serialize_variables",
]
