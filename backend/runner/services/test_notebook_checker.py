import io
import tempfile
from pathlib import Path
from django.test import TestCase
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from ..models import (
    Contest, Notebook, Cell, NotebookSubmission,
    Problem, ProblemData, ProblemDescriptor, Course
)
from ..services.notebook_checker import NotebookSubmissionChecker

User = get_user_model()


class NotebookSubmissionCheckerTests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.media_root = Path(self.tmpdir.name)
        
        # Create users
        self.teacher = User.objects.create_user(username="teacher1", password="pass")
        self.student = User.objects.create_user(username="student1", password="pass")
        
        # Create course
        self.course = Course.objects.create(
            title="ML Course",
            owner=self.teacher,
            is_open=True
        )
        
        # Create problem with data
        self.problem = Problem.objects.create(
            title="Test Problem",
            created_at=timezone.now().date()
        )
        
        ProblemDescriptor.objects.create(
            problem=self.problem,
            id_column="id",
            target_column="value",
            target_type="int",
            check_order=False
        )
        
        # Create problem data with answer file
        self.problem_data = ProblemData.objects.create(problem=self.problem)
        answer_csv = "id,value\n1,10\n2,20\n3,30\n"
        self.problem_data.answer_file.save(
            "answer.csv",
            ContentFile(answer_csv),
            save=True
        )
        
        # Create notebook contest
        self.contest = Contest.objects.create(
            title="Notebook Contest",
            course=self.course,
            contest_type=Contest.ContestType.NOTEBOOK,
            created_by=self.teacher
        )
        
        # Create student notebook
        self.notebook = Notebook.objects.create(
            title="Student Solution",
            owner=self.student
        )
    
    def tearDown(self):
        self.tmpdir.cleanup()
    
    def test_check_single_task_cell_success(self):
        """Test checking a single task cell with correct output"""
        # Create task cell with correct output
        task_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="# some code",
            output="id,value\n1,10\n2,20\n3,30\n",
            is_task_cell=True,
            problem=self.problem,
            execution_order=1
        )
        
        # Create submission
        submission = NotebookSubmission.objects.create(
            user=self.student,
            contest=self.contest,
            notebook=self.notebook
        )
        
        # Check submission
        checker = NotebookSubmissionChecker()
        result = checker.check_notebook_submission(submission)
        
        self.assertTrue(result.ok)
        self.assertIn(task_cell.id, result.cell_results)
        cell_result = result.cell_results[task_cell.id]
        self.assertTrue(cell_result["success"])
        self.assertEqual(cell_result["score"], 1.0)
        
        # Check submission was updated
        submission.refresh_from_db()
        self.assertEqual(submission.status, NotebookSubmission.STATUS_ACCEPTED)
        self.assertEqual(submission.total_score, 1.0)
    
    def test_check_single_task_cell_wrong_output(self):
        """Test checking a single task cell with incorrect output"""
        # Create task cell with wrong output
        task_cell = Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="# some code",
            output="id,value\n1,99\n2,99\n3,99\n",  # wrong values
            is_task_cell=True,
            problem=self.problem,
            execution_order=1
        )
        
        # Create submission
        submission = NotebookSubmission.objects.create(
            user=self.student,
            contest=self.contest,
            notebook=self.notebook
        )
        
        # Check submission
        checker = NotebookSubmissionChecker()
        result = checker.check_notebook_submission(submission)
        
        self.assertTrue(result.ok)
        self.assertIn(task_cell.id, result.cell_results)
        cell_result = result.cell_results[task_cell.id]
        self.assertTrue(cell_result["success"])
        self.assertEqual(cell_result["score"], 0.0)
        
        # Check submission was updated
        submission.refresh_from_db()
        self.assertEqual(submission.status, NotebookSubmission.STATUS_FAILED)
        self.assertEqual(submission.total_score, 0.0)
    
    def test_check_multiple_task_cells(self):
        """Test checking multiple task cells"""
        # Create two task cells with different results
        Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="# task 1",
            output="id,value\n1,10\n2,20\n3,30\n",  # correct
            is_task_cell=True,
            problem=self.problem,
            execution_order=1
        )
        
        Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="# task 2",
            output="id,value\n1,99\n2,99\n3,99\n",  # wrong
            is_task_cell=True,
            problem=self.problem,
            execution_order=2
        )
        
        # Create submission
        submission = NotebookSubmission.objects.create(
            user=self.student,
            contest=self.contest,
            notebook=self.notebook
        )
        
        # Check submission
        checker = NotebookSubmissionChecker()
        result = checker.check_notebook_submission(submission)
        
        self.assertTrue(result.ok)
        self.assertEqual(len(result.cell_results), 2)
        
        # Average score should be 0.5 (1.0 + 0.0) / 2
        # Status should be FAILED since not all tasks passed
        submission.refresh_from_db()
        self.assertEqual(submission.total_score, 0.5)
        self.assertEqual(submission.status, NotebookSubmission.STATUS_FAILED)
    
    def test_check_cell_without_output(self):
        """Test checking a cell with no output"""
        # Create task cell with no output
        Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="# some code",
            output="",  # empty output
            is_task_cell=True,
            problem=self.problem,
            execution_order=1
        )
        
        # Create submission
        submission = NotebookSubmission.objects.create(
            user=self.student,
            contest=self.contest,
            notebook=self.notebook
        )
        
        # Check submission
        checker = NotebookSubmissionChecker()
        result = checker.check_notebook_submission(submission)
        
        self.assertTrue(result.ok)
        # Should have error for cell with no output
        cell_result = list(result.cell_results.values())[0]
        self.assertFalse(cell_result["success"])
        self.assertIn("no output", cell_result["error"].lower())
    
    def test_check_regular_contest_error(self):
        """Test that checking fails for non-notebook contests"""
        # Create regular contest
        regular_contest = Contest.objects.create(
            title="Regular Contest",
            course=self.course,
            contest_type=Contest.ContestType.REGULAR,
            created_by=self.teacher
        )
        
        # Create submission for regular contest
        submission = NotebookSubmission.objects.create(
            user=self.student,
            contest=regular_contest,
            notebook=self.notebook
        )
        
        # Check submission
        checker = NotebookSubmissionChecker()
        result = checker.check_notebook_submission(submission)
        
        self.assertFalse(result.ok)
        self.assertIn("not a notebook-based contest", result.errors)
    
    def test_check_notebook_without_task_cells(self):
        """Test that checking fails for notebooks without task cells"""
        # Don't create any task cells
        
        # Create submission
        submission = NotebookSubmission.objects.create(
            user=self.student,
            contest=self.contest,
            notebook=self.notebook
        )
        
        # Check submission
        checker = NotebookSubmissionChecker()
        result = checker.check_notebook_submission(submission)
        
        self.assertFalse(result.ok)
        self.assertIn("No task cells found", result.errors)
