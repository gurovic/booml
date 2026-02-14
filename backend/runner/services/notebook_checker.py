# runner/services/notebook_checker.py
import io
import logging
from typing import Dict, Any, Optional

import pandas as pd

from ..models.notebook_submission import NotebookSubmission
from ..models.cell import Cell
from ..models.problem_desriptor import ProblemDescriptor
from .checker import SubmissionChecker

logger = logging.getLogger(__name__)


class NotebookCheckResult:
    """Result of checking a notebook submission"""
    
    def __init__(self, ok: bool, cell_results: Optional[Dict[int, Dict[str, Any]]] = None, errors: str = ""):
        self.ok = ok
        self.cell_results = cell_results or {}
        self.errors = errors


class NotebookSubmissionChecker:
    """
    Checker for notebook-based contest submissions.
    Validates outputs from code cells against expected results using CSV matching.
    """
    
    def __init__(self):
        self.submission_checker = SubmissionChecker()
    
    def check_notebook_submission(self, notebook_submission: NotebookSubmission) -> NotebookCheckResult:
        """
        Main function to check a notebook submission.
        Iterates through task cells and checks their outputs.
        """
        logger.info(
            "Starting check for notebook submission %s",
            getattr(notebook_submission, "id", "?")
        )
        
        contest = notebook_submission.contest
        notebook = notebook_submission.notebook
        
        # Verify it's a notebook contest
        if not hasattr(contest, 'contest_type') or contest.contest_type != 'notebook':
            return NotebookCheckResult(
                False,
                errors="Contest is not a notebook-based contest"
            )
        
        # Get all task cells in the notebook
        task_cells = notebook.cells.filter(is_task_cell=True).order_by('execution_order')
        
        if not task_cells.exists():
            return NotebookCheckResult(
                False,
                errors="No task cells found in notebook"
            )
        
        cell_results = {}
        total_score = 0.0
        total_tasks = 0
        
        for task_cell in task_cells:
            cell_result = self._check_task_cell(task_cell)
            cell_results[task_cell.id] = cell_result
            
            if cell_result["success"]:
                total_score += cell_result.get("score", 0.0)
                total_tasks += 1
            else:
                logger.warning(
                    "Task cell %s failed: %s",
                    task_cell.id,
                    cell_result.get("error", "Unknown error")
                )
        
        # Calculate average score
        avg_score = total_score / total_tasks if total_tasks > 0 else 0.0
        
        # Update notebook submission
        notebook_submission.metrics = cell_results
        notebook_submission.total_score = avg_score
        notebook_submission.status = NotebookSubmission.STATUS_ACCEPTED if avg_score > 0 else NotebookSubmission.STATUS_FAILED
        notebook_submission.save(update_fields=["metrics", "total_score", "status"])
        
        logger.info(
            "Check completed for notebook submission %s. Total score: %.4f (%d/%d tasks)",
            getattr(notebook_submission, "id", "?"),
            avg_score,
            int(total_score),
            total_tasks
        )
        
        return NotebookCheckResult(
            ok=True,
            cell_results=cell_results
        )
    
    def _check_task_cell(self, task_cell: Cell) -> Dict[str, Any]:
        """
        Check a single task cell by validating its output against the problem's expected answer.
        Uses CSV matching logic from SubmissionChecker.
        """
        problem = task_cell.problem
        
        if not problem:
            return {
                "success": False,
                "error": "Task cell has no associated problem",
                "score": 0.0
            }
        
        problem_data = getattr(problem, "data", None)
        descriptor = getattr(problem, "descriptor", None)
        
        if not problem_data:
            return {
                "success": False,
                "error": "ProblemData not found for this task",
                "score": 0.0
            }
        
        if not descriptor:
            return {
                "success": False,
                "error": "ProblemDescriptor not found for this task",
                "score": 0.0
            }
        
        # Parse cell output as CSV
        cell_output = task_cell.output
        if not cell_output or not cell_output.strip():
            return {
                "success": False,
                "error": "Cell has no output",
                "score": 0.0
            }
        
        try:
            submission_df = pd.read_csv(io.StringIO(cell_output))
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse cell output as CSV: {str(e)}",
                "score": 0.0
            }
        
        # Load ground truth
        ground_truth_file = self._select_ground_truth_file(problem_data)
        ground_truth_df = self._load_ground_truth(ground_truth_file)
        
        if ground_truth_df is None:
            return {
                "success": False,
                "error": "Failed to load ground truth from problem data",
                "score": 0.0
            }
        
        # Use CSV match checking from SubmissionChecker
        metric_result = self.submission_checker._calculate_csv_match(
            submission_df,
            ground_truth_df,
            descriptor,
            "csv_match"
        )
        
        return metric_result
    
    def _select_ground_truth_file(self, problem_data):
        """Returns the answer file (answer_file -> test_file fallback)."""
        for attr in ("answer_file", "test_file"):
            file_field = getattr(problem_data, attr, None)
            file_name = getattr(file_field, "name", "")
            if file_field and file_name:
                return file_field
        logger.warning(
            "No answer/test files available for problem %s",
            getattr(problem_data, "problem_id", "?")
        )
        return None
    
    def _load_ground_truth(self, file_field) -> Optional[pd.DataFrame]:
        """Load ground truth from ProblemData"""
        if not file_field:
            return None
        path = getattr(file_field, "path", None)
        if not path:
            logger.warning("Ground truth file has no path (maybe not saved yet)")
            return None
        try:
            return pd.read_csv(path)
        except Exception:
            logger.info("Failed to load ground truth file %s", path)
            return None
