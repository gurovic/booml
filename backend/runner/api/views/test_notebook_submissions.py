import tempfile
from pathlib import Path
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.files.base import ContentFile
from rest_framework.test import APIRequestFactory, force_authenticate

from ...models import (
    Contest, Notebook, Cell, NotebookSubmission,
    Problem, ProblemData, ProblemDescriptor, Course
)
from .notebook_submissions import (
    NotebookSubmissionCreateView,
    NotebookSubmissionListView,
    NotebookSubmissionDetailView
)

User = get_user_model()


class NotebookSubmissionAPITests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.media_root = Path(self.tmpdir.name)
        
        # Create users
        self.teacher = User.objects.create_user(username="teacher1", password="pass")
        self.student = User.objects.create_user(username="student1", password="pass")
        
        # Login as student
        self.client.login(username="student1", password="pass")
        
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
        
        # Create student notebook with task cell
        self.notebook = Notebook.objects.create(
            title="Student Solution",
            owner=self.student
        )
        
        Cell.objects.create(
            notebook=self.notebook,
            cell_type=Cell.CODE,
            content="# solution code",
            output="id,value\n1,10\n2,20\n3,30\n",
            is_task_cell=True,
            problem=self.problem,
            execution_order=1
        )
        
        self.url = reverse("notebook-submission-create")
        self.factory = APIRequestFactory()
    
    def tearDown(self):
        self.tmpdir.cleanup()
    
    def test_create_notebook_submission_success(self):
        """Test creating a notebook submission with valid data"""
        data = {
            "contest_id": self.contest.id,
            "notebook_id": self.notebook.id
        }
        
        resp = self.client.post(self.url, data, content_type="application/json")
        
        self.assertEqual(resp.status_code, 201)
        response_data = resp.json()
        
        # Check response contains expected fields
        self.assertIn("id", response_data)
        self.assertEqual(response_data["contest_id"], self.contest.id)
        self.assertEqual(response_data["notebook_id"], self.notebook.id)
        self.assertEqual(response_data["status"], NotebookSubmission.STATUS_ACCEPTED)
        self.assertEqual(response_data["total_score"], 1.0)
        
        # Verify submission was created
        submission = NotebookSubmission.objects.first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.user, self.student)
        self.assertEqual(submission.contest, self.contest)
        self.assertEqual(submission.notebook, self.notebook)
    
    def test_create_submission_invalid_contest(self):
        """Test creating submission with non-existent contest"""
        data = {
            "contest_id": 99999,
            "notebook_id": self.notebook.id
        }
        
        resp = self.client.post(self.url, data, content_type="application/json")
        
        self.assertEqual(resp.status_code, 400)
        self.assertIn("contest_id", resp.json())
    
    def test_create_submission_regular_contest(self):
        """Test that creating submission for regular contest fails"""
        regular_contest = Contest.objects.create(
            title="Regular Contest",
            course=self.course,
            contest_type=Contest.ContestType.REGULAR,
            created_by=self.teacher
        )
        
        data = {
            "contest_id": regular_contest.id,
            "notebook_id": self.notebook.id
        }
        
        resp = self.client.post(self.url, data, content_type="application/json")
        
        self.assertEqual(resp.status_code, 400)
        response_data = resp.json()
        self.assertIn("contest_id", response_data)
        self.assertIn("not a notebook-based contest", str(response_data))
    
    def test_create_submission_other_users_notebook(self):
        """Test that user cannot submit another user's notebook"""
        other_user = User.objects.create_user(username="other", password="pass")
        other_notebook = Notebook.objects.create(
            title="Other's Notebook",
            owner=other_user
        )
        
        data = {
            "contest_id": self.contest.id,
            "notebook_id": other_notebook.id
        }
        
        resp = self.client.post(self.url, data, content_type="application/json")
        
        self.assertEqual(resp.status_code, 400)
        response_data = resp.json()
        self.assertIn("notebook_id", response_data)
        self.assertIn("your own notebooks", str(response_data))
    
    def test_create_submission_no_task_cells(self):
        """Test that submission fails if notebook has no task cells"""
        empty_notebook = Notebook.objects.create(
            title="Empty Notebook",
            owner=self.student
        )
        
        data = {
            "contest_id": self.contest.id,
            "notebook_id": empty_notebook.id
        }
        
        resp = self.client.post(self.url, data, content_type="application/json")
        
        self.assertEqual(resp.status_code, 400)
        response_data = resp.json()
        self.assertIn("notebook_id", response_data)
        self.assertIn("no task cells", str(response_data))
    
    def test_list_user_submissions(self):
        """Test listing user's notebook submissions"""
        # Create two submissions
        NotebookSubmission.objects.create(
            user=self.student,
            contest=self.contest,
            notebook=self.notebook,
            status=NotebookSubmission.STATUS_ACCEPTED,
            total_score=1.0
        )
        
        NotebookSubmission.objects.create(
            user=self.student,
            contest=self.contest,
            notebook=self.notebook,
            status=NotebookSubmission.STATUS_FAILED,
            total_score=0.0
        )
        
        # Create submission for other user (should not be in list)
        other_user = User.objects.create_user(username="other", password="pass")
        other_notebook = Notebook.objects.create(owner=other_user)
        NotebookSubmission.objects.create(
            user=other_user,
            contest=self.contest,
            notebook=other_notebook
        )
        
        url = reverse("notebook-submission-list")
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 200)
        response_data = resp.json()
        
        # Should only see own submissions
        self.assertEqual(response_data["count"], 2)
        results = response_data["results"]
        self.assertEqual(len(results), 2)
        
        # Verify submissions are ordered by submitted_at DESC
        self.assertGreater(results[0]["id"], results[1]["id"])
    
    def test_get_submission_detail(self):
        """Test getting details of a specific submission"""
        submission = NotebookSubmission.objects.create(
            user=self.student,
            contest=self.contest,
            notebook=self.notebook,
            status=NotebookSubmission.STATUS_ACCEPTED,
            total_score=0.95,
            metrics={"1": {"score": 1.0}, "2": {"score": 0.9}}
        )
        
        url = reverse("notebook-submission-detail", kwargs={"pk": submission.id})
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 200)
        response_data = resp.json()
        
        self.assertEqual(response_data["id"], submission.id)
        self.assertEqual(response_data["total_score"], 0.95)
        self.assertEqual(response_data["status"], NotebookSubmission.STATUS_ACCEPTED)
        self.assertIsNotNone(response_data["metrics"])
    
    def test_cannot_access_other_users_submission(self):
        """Test that users cannot access other users' submissions"""
        other_user = User.objects.create_user(username="other", password="pass")
        other_notebook = Notebook.objects.create(owner=other_user)
        submission = NotebookSubmission.objects.create(
            user=other_user,
            contest=self.contest,
            notebook=other_notebook
        )
        
        url = reverse("notebook-submission-detail", kwargs={"pk": submission.id})
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 404)
    
    def test_unauthenticated_user_cannot_create_submission(self):
        """Test that unauthenticated users cannot create submissions"""
        self.client.logout()
        
        data = {
            "contest_id": self.contest.id,
            "notebook_id": self.notebook.id
        }
        
        resp = self.client.post(self.url, data, content_type="application/json")
        
        self.assertEqual(resp.status_code, 403)
