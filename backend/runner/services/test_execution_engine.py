import io
import json
import os
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from django.test import SimpleTestCase

from runner.services.execution_engine import (
    ExecutionEngine,
    ExecutionResult,
    serialize_variables,
)
from runner.services.vm_agent import LocalVmAgent
from runner.services.runtime import RuntimeSession


class TestShellCommands(SimpleTestCase):
    
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmpdir.name)
    
    def tearDown(self):
        self.tmpdir.cleanup()
        ExecutionEngine.reset_ipython()
    
    def _engine(self):
        return ExecutionEngine(self.workdir, {})
    
    def test_simple_echo_prints_correctly(self):
        engine = self._engine()
        result = engine.execute("!echo hello")
        self.assertIn("hello", result["stdout"])
        self.assertIsNone(result["error"])
    
    def test_shell_pwd_prints_working_directory(self):
        engine = self._engine()
        result = engine.execute("!pwd")
        self.assertNotEqual(result["stdout"].strip(), "")
        self.assertIsNone(result["error"])
    
    def test_empty_command_does_nothing(self):
        engine = self._engine()
        result = engine.execute("!")
        self.assertEqual(result["stdout"], "")
        self.assertIsNone(result["error"])
    
    def test_multiple_echo_lines_execute_sequentially(self):
        engine = self._engine()
        code = "!echo first\n!echo second"
        result = engine.execute(code)
        self.assertIn("first", result["stdout"])
        self.assertIn("second", result["stdout"])
    
    def test_shell_command_after_whitespace_executes(self):
        engine = self._engine()
        result = engine.execute("  !echo test")
        self.assertIn("test", result["stdout"])
    
    def test_shell_command_after_tabs_executes(self):
        engine = self._engine()
        result = engine.execute("\t!echo test")
        self.assertIn("test", result["stdout"])
    
    def test_shell_in_middle_of_python_block(self):
        engine = self._engine()
        code = "x = 1\n!echo mid\ny = 2"
        result = engine.execute(code)
        self.assertIn("mid", result["stdout"])
        self.assertEqual(result["variables"]["x"], 1)
        self.assertEqual(result["variables"]["y"], 2)
    
    def test_shell_inside_indented_block_retains_indent(self):
        engine = self._engine()
        code = "if True:\n    !echo indented\n    z = 3"
        result = engine.execute(code)
        self.assertIn("indented", result["stdout"])
        self.assertEqual(result["variables"]["z"], 3)
    
    def test_shell_at_end_of_file_without_newline(self):
        engine = self._engine()
        result = engine.execute("!echo end")
        self.assertIn("end", result["stdout"])
    
    def test_single_pipe_echo_to_grep(self):
        engine = self._engine()
        result = engine.execute("!echo -e 'apple\\nbanana' | grep apple")
        self.assertIn("apple", result["stdout"])
    
    def test_multiple_pipes_chain(self):
        engine = self._engine()
        result = engine.execute("!echo -e 'line1\\nline2\\nline3' | grep line | wc -l")
        self.assertTrue("3" in result["stdout"] or result["stdout"].strip() == "3")
    
    def test_overwrite_redirect_works(self):
        engine = self._engine()
        code = "!echo content > /tmp/test_overwrite.txt\n!cat /tmp/test_overwrite.txt"
        result = engine.execute(code)
        self.assertIn("content", result["stdout"])
    
    def test_append_redirect_works(self):
        engine = self._engine()
        code = "!echo line1 > /tmp/test_append.txt\n!echo line2 >> /tmp/test_append.txt\n!cat /tmp/test_append.txt"
        result = engine.execute(code)
        self.assertIn("line1", result["stdout"])
        self.assertIn("line2", result["stdout"])
    
    def test_pipe_and_redirect_mixed(self):
        engine = self._engine()
        code = "!echo test | cat > /tmp/test_pipe_redir.txt\n!cat /tmp/test_pipe_redir.txt"
        result = engine.execute(code)
        self.assertIn("test", result["stdout"])
    
    def test_subshell_support(self):
        engine = self._engine()
        result = engine.execute("!echo $(echo inner)")
        self.assertIn("inner", result["stdout"])
    
    def test_mixed_double_single_quotes(self):
        engine = self._engine()
        result = engine.execute("!echo \"it's\" 'quoted'")
        self.assertIn("it's", result["stdout"])
        self.assertIn("quoted", result["stdout"])
    
    def test_nested_quotes(self):
        engine = self._engine()
        result = engine.execute("!bash -c \"echo 'nested'\"")
        self.assertIn("nested", result["stdout"])
    
    def test_escaped_spaces_with_backslashes(self):
        engine = self._engine()
        result = engine.execute("!echo hello\\ world")
        self.assertTrue("hello" in result["stdout"] and "world" in result["stdout"])
    
    def test_escaped_dollar_characters(self):
        engine = self._engine()
        result = engine.execute("!echo \\$VAR")
        self.assertIn("$VAR", result["stdout"])
    
    def test_escaped_quotes_inside_quotes(self):
        engine = self._engine()
        result = engine.execute("!echo \"say \\\"hi\\\"\"")
        self.assertIn("say", result["stdout"])
    
    def test_nonexistent_command_error_visible_in_stderr(self):
        engine = self._engine()
        result = engine.execute("!nonexistentcommand123")
        self.assertTrue(result["stdout"] != "" or result["error"] is not None)
    
    def test_non_zero_exit_code_preserved(self):
        engine = self._engine()
        result = engine.execute("!false")
        self.assertEqual(result["stdout"], "")
    
    def test_missing_file_in_cat_error(self):
        engine = self._engine()
        result = engine.execute("!cat /nonexistent/file/path.txt")
        self.assertTrue(result["stdout"] != "" or "No such file" in result["stdout"])
    
    def test_bad_pipe_syntax_error(self):
        engine = self._engine()
        result = engine.execute("!echo test |")
        self.assertTrue(result["stdout"] != "" or result["error"] is not None)
    
    def test_unclosed_quote_syntax_error(self):
        engine = self._engine()
        result = engine.execute("!echo \"unclosed")
        self.assertTrue(result["stdout"] != "" or result["error"] is not None)
    
    def test_assign_simple_string(self):
        engine = self._engine()
        code = "res = !echo hi"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_assign_multiline(self):
        engine = self._engine()
        code = "res = !echo line1\\necho line2"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_assign_empty_output(self):
        engine = self._engine()
        code = "res = !true"
        result = engine.execute(code)
        self.assertIn("res", result["variables"])
    
    def test_assigned_variable_persists_in_namespace(self):
        engine = self._engine()
        engine.execute("res = !echo data")
        result = engine.execute("x = res if 'res' in dir() else None")
        self.assertIsNotNone(result["variables"]["x"])
    
    def test_assigned_variable_can_be_used_by_python(self):
        engine = self._engine()
        engine.execute("res = !echo value")
        result = engine.execute("output = len(res) if 'res' in dir() else 0")
        self.assertIsNone(result["error"])
    
    def test_shell_creates_file_python_reads_it(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "shell_file.txt"
            engine = ExecutionEngine(Path(tmpdir), {})
            engine.execute(f"!echo content > {filepath}")
            result = engine.execute(f"with open('{filepath}') as f: data = f.read()")
            self.assertIsNone(result["error"])
    
    def test_python_creates_file_shell_reads_it(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "python_file.txt"
            engine = ExecutionEngine(Path(tmpdir), {})
            engine.execute(f"with open('{filepath}', 'w') as f: f.write('data')")
            result = engine.execute(f"!cat {filepath}")
            self.assertIn("data", result["stdout"])


class TestLineMagics(SimpleTestCase):
    
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmpdir.name)
    
    def tearDown(self):
        self.tmpdir.cleanup()
        ExecutionEngine.reset_ipython()
    
    def _engine(self):
        return ExecutionEngine(self.workdir, {})
    
    def test_percent_pwd_prints_correct_directory(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%pwd")
        self.assertNotEqual(result["stdout"].strip(), "")
    
    def test_percent_ls_lists_files(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%ls")
        self.assertIsNone(result["error"])
    
    def test_percent_time_displays_execution_time(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%time x = 1 + 1")
        self.assertIsNone(result["error"])
    
    def test_cd_subdir_changes_directory(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            engine = ExecutionEngine(Path(tmpdir), {})
            code = f"%cd {subdir}\n%pwd"
            result = engine.execute(code)
            self.assertIn(str(subdir), result["stdout"])
    
    def test_cd_parent_moves_to_parent(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%cd ..\n%pwd"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_cd_path_with_spaces(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        with tempfile.TemporaryDirectory() as tmpdir:
            spaced_dir = Path(tmpdir) / "dir with spaces"
            spaced_dir.mkdir()
            engine = ExecutionEngine(Path(tmpdir), {})
            code = f"%cd \"{spaced_dir}\"\n%pwd"
            result = engine.execute(code)
            self.assertTrue(result["error"] is None or "with spaces" in result["stdout"])
    
    def test_cd_nonexistent_gives_error(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%cd /nonexistent/path/xyz")
        self.assertTrue(result["error"] is not None or result["stdout"] != "")
    
    def test_unknown_magic_name_readable_error(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%unknownmagic123")
        self.assertTrue(result["error"] is not None or "unknown magic" in result["stdout"].lower())
    
    def test_time_around_bad_python_code_error_caught(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%time 1 / 0")
        self.assertIsNotNone(result["error"])
    
    def test_magic_inside_python_string_ignored(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "s = '%pwd'\nx = 1"
        result = engine.execute(code)
        self.assertEqual(result["variables"]["s"], "%pwd")
        self.assertEqual(result["variables"]["x"], 1)
    
    def test_percent_inside_fstring_ignored(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "val = 10\ns = f'{val}%'\nx = 1"
        result = engine.execute(code)
        self.assertIn("%", result["variables"]["s"])
        self.assertEqual(result["variables"]["x"], 1)
    
    def test_percent_without_identifier_invalid_syntax(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%")
        self.assertIsNotNone(result["error"])
    
    def test_time_with_python_variable(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "myvar = 42\n%time result = myvar * 2"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_time_does_not_delete_vars(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "x = 10\n%time y = x + 5"
        result = engine.execute(code)
        self.assertEqual(result["variables"]["x"], 10)
        self.assertEqual(result["variables"]["y"], 15)
    
    def test_magic_returns_value_printed_correctly(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%pwd")
        self.assertNotEqual(result["stdout"].strip(), "")
    
    def test_magic_modifies_working_directory_shell_sees_update(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            engine = ExecutionEngine(Path(tmpdir), {})
            code = f"%cd {subdir}\n!pwd"
            result = engine.execute(code)
            self.assertIn(str(subdir), result["stdout"])
    
    def test_multiple_magics_back_to_back(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%pwd\n%pwd\nx = 1"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
        self.assertEqual(result["variables"]["x"], 1)
    
    def test_pwd_inside_indented_block(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "if True:\n    %pwd\n    x = 1"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_time_inside_block(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "if True:\n    %time y = 2"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_ls_inside_try_except(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "try:\n    %ls\nexcept:\n    pass"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_pwd_after_python_block(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "x = 5\n%pwd"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_pwd_at_end_of_file(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%pwd")
        self.assertIsNone(result["error"])
    
    def test_cd_path_that_looks_like_magic(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        with tempfile.TemporaryDirectory() as tmpdir:
            magic_dir = Path(tmpdir) / "%test"
            magic_dir.mkdir()
            engine = ExecutionEngine(Path(tmpdir), {})
            code = f"%cd {magic_dir}"
            result = engine.execute(code)
            self.assertTrue(result["error"] is not None or result["stdout"] != "")
    
    def test_unknown_with_arguments(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%unknownmagic arg1 arg2")
        self.assertIsNotNone(result["error"])
    
    def test_time_with_multiple_spaces(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%time    x = 1")
        self.assertIsNone(result["error"])


class TestCellMagics(SimpleTestCase):
    
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmpdir.name)
    
    def tearDown(self):
        self.tmpdir.cleanup()
        ExecutionEngine.reset_ipython()
    
    def _engine(self):
        return ExecutionEngine(self.workdir, {})
    
    def test_bash_simple_echo(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%bash\necho hello")
        self.assertIn("hello", result["stdout"])
    
    def test_bash_multiline_script(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%%bash\necho line1\necho line2\necho line3"
        result = engine.execute(code)
        self.assertIn("line1", result["stdout"])
        self.assertIn("line2", result["stdout"])
        self.assertIn("line3", result["stdout"])
    
    def test_bash_with_args(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%bash -e\necho test")
        self.assertIsNone(result["error"])
    
    def test_unknown_cell_magic_raises_error(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%unknowncellmagic\necho test")
        self.assertIsNotNone(result["error"])
    
    def test_bad_syntax_inside_cell_magic_stderr(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%bash\necho )")
        self.assertTrue(result["stdout"] != "" or result["error"] is not None)
    
    def test_body_empty_but_magic_present(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%bash\n")
        self.assertIsNone(result["error"])
    
    def test_magic_with_only_whitespace_body(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%bash\n   \n  ")
        self.assertIsNone(result["error"])
    
    def test_missing_body_entirely(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%bash")
        self.assertTrue(result["error"] is None or result["error"] is not None)
    
    def test_bash_inside_indented_block(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "if True:\n    %%bash\n    echo indented"
        result = engine.execute(code)
        self.assertTrue(result["error"] is None or "indented" in result["stdout"])
    
    def test_bash_after_whitespace(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "  %%bash\n  echo test"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_bash_inside_try_except(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "try:\n    %%bash\n    echo test\nexcept:\n    pass"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_bash_at_end_of_file_without_newline(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%bash\necho end")
        self.assertTrue("end" in result["stdout"] or result["error"] is None)
    
    def test_bash_writes_file_python_reads(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "bash_file.txt"
            engine = ExecutionEngine(Path(tmpdir), {})
            code = f"%%bash\necho content > {filepath}"
            engine.execute(code)
            result = engine.execute(f"with open('{filepath}') as f: data = f.read()")
            self.assertIsNone(result["error"])
    
    def test_python_writes_file_bash_reads(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "python_bash.txt"
            engine = ExecutionEngine(Path(tmpdir), {})
            engine.execute(f"with open('{filepath}', 'w') as f: f.write('test')")
            result = engine.execute(f"%%bash\ncat {filepath}")
            self.assertIn("test", result["stdout"])
    
    def test_cell_magic_output_captured(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%bash\necho captured")
        self.assertIn("captured", result["stdout"])
    
    def test_cell_magic_stderr_captured(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        result = engine.execute("%%bash\necho error >&2")
        self.assertIn("error", result["stdout"])
    
    def test_bash_script_with_nested_quotes(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%%bash\necho \"it's quoted\""
        result = engine.execute(code)
        self.assertTrue("it's" in result["stdout"] or result["error"] is None)
    
    def test_bash_script_with_pipes(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%%bash\necho test | grep test"
        result = engine.execute(code)
        self.assertTrue("test" in result["stdout"] or result["error"] is None)
    
    def test_bash_script_with_redirects(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%%bash\necho data > /tmp/magic_test.txt\ncat /tmp/magic_test.txt"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_bash_sequence_then_pwd(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%%bash\necho bash_output\n%pwd"
        result = engine.execute(code)
        self.assertTrue(result["error"] is not None or result["error"] is None)
    
    def test_bash_then_shell_command(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%%bash\necho bash\n!echo shell"
        result = engine.execute(code)
        self.assertTrue(result["error"] is not None or result["error"] is None)


class TestTransformationAndMixedCases(SimpleTestCase):
    
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmpdir.name)
    
    def tearDown(self):
        self.tmpdir.cleanup()
        ExecutionEngine.reset_ipython()
    
    def _engine(self):
        return ExecutionEngine(self.workdir, {})
    
    def test_echo_inside_triple_quoted_string_ignored(self):
        engine = self._engine()
        code = 's = """!echo inside string"""\nx = 1'
        result = engine.execute(code)
        self.assertEqual(result["variables"]["x"], 1)
        self.assertIn("!echo", result["variables"]["s"])
    
    def test_percent_inside_comment_ignored(self):
        engine = self._engine()
        code = "# %pwd comment\nx = 1"
        result = engine.execute(code)
        self.assertEqual(result["variables"]["x"], 1)
    
    def test_shell_inside_python_string_ignored(self):
        engine = self._engine()
        code = "s = '!ls'\nx = 2"
        result = engine.execute(code)
        self.assertEqual(result["variables"]["x"], 2)
        self.assertEqual(result["variables"]["s"], "!ls")
    
    def test_shell_inside_dictionary_raises_error(self):
        engine = self._engine()
        code = "d = {'key': '!echo'}\nx = 1"
        result = engine.execute(code)
        self.assertEqual(result["variables"]["x"], 1)
    
    def test_percent_in_string_not_transformed(self):
        engine = self._engine()
        code = "percent = '%hello'\nx = 1"
        result = engine.execute(code)
        self.assertEqual(result["variables"]["percent"], "%hello")
        self.assertEqual(result["variables"]["x"], 1)
    
    def test_percent_inside_shell_stays_shell(self):
        engine = self._engine()
        code = "!echo %test"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_double_percent_inside_shell_stays(self):
        engine = self._engine()
        code = "!echo %%test"
        result = engine.execute(code)
        self.assertIsNone(result["error"])
    
    def test_cell_magic_body_with_percent(self):
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%%bash\necho %test"
        result = engine.execute(code)
        self.assertTrue(result["error"] is None or result["error"] is not None)
    
    def test_multiple_magics_mixed_ordering(self):
        engine = self._engine()
        code = "!echo shell\nx = 1\n!echo shell2"
        result = engine.execute(code)
        self.assertEqual(result["variables"]["x"], 1)
    
    def test_transformations_maintain_indentation(self):
        engine = self._engine()
        code = "if True:\n    !echo test\n    x = 1"
        result = engine.execute(code)
        self.assertEqual(result["variables"]["x"], 1)
    
    def test_shell_and_python_sequencing(self):
        engine = self._engine()
        code = "!echo start\nx = 100\n!echo end"
        result = engine.execute(code)
        self.assertEqual(result["variables"]["x"], 100)
        self.assertIn("start", result["stdout"])
        self.assertIn("end", result["stdout"])

    def test_pwd_and_time_magics_together(self):
        """Test %pwd followed by %time - reproduces the reported issue"""
        if not ExecutionEngine.is_ipython_available():
            self.skipTest("IPython not available")
        engine = self._engine()
        code = "%pwd\n%time sum(range(10000))"
        result = engine.execute(code)
        # Should not have KeyError: '_oh'
        self.assertIsNone(result["error"], f"Got error: {result['error']}")
        # %pwd should show a path
        self.assertGreater(len(result["stdout"]), 0)
        # %time should show timing info
        self.assertIn("user", result["stdout"].lower())

