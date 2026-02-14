from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model

from ..models.contest import Contest
from ..models.notebook import Notebook
from ..models.notebook_submission import NotebookSubmission
from ..models.course import Course

User = get_user_model()


class NotebookSubmissionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student1", password="pass")
        self.teacher = User.objects.create_user(username="teacher1", password="pass")
        
        # Create a course
        self.course = Course.objects.create(
            title="ML Course",
            owner=self.teacher,
            is_open=True
        )
        
        # Create a notebook contest
        self.contest = Contest.objects.create(
            title="Notebook Contest 1",
            course=self.course,
            contest_type=Contest.ContestType.NOTEBOOK,
            created_by=self.teacher
        )
        
        # Create a notebook
        self.notebook = Notebook.objects.create(
            title="Student Solution",
            owner=self.user
        )
    
    def test_create_notebook_submission(self):
        """Test creating a notebook submission"""
        submission = NotebookSubmission.objects.create(
            user=self.user,
            contest=self.contest,
            notebook=self.notebook
        )
        
        self.assertEqual(submission.status, NotebookSubmission.STATUS_PENDING)
        self.assertIsNone(submission.total_score)
        self.assertIsNone(submission.metrics)
        
        # Test string representation
        self.assertIn(self.user.username, str(submission))
        self.assertIn(str(self.contest.id), str(submission))
    
    def test_submission_with_metrics(self):
        """Test notebook submission with metrics and score"""
        metrics_data = {
            "1": {"score": 1.0, "metric": "csv_match"},
            "2": {"score": 0.8, "metric": "csv_match"}
        }
        
        submission = NotebookSubmission.objects.create(
            user=self.user,
            contest=self.contest,
            notebook=self.notebook,
            status=NotebookSubmission.STATUS_ACCEPTED,
            metrics=metrics_data,
            total_score=0.9
        )
        
        self.assertEqual(submission.status, NotebookSubmission.STATUS_ACCEPTED)
        self.assertEqual(submission.total_score, 0.9)
        self.assertEqual(submission.metrics, metrics_data)
    
    def test_submission_ordering(self):
        """Test that submissions are ordered by submitted_at DESC"""
        sub1 = NotebookSubmission.objects.create(
            user=self.user,
            contest=self.contest,
            notebook=self.notebook
        )
        
        sub2 = NotebookSubmission.objects.create(
            user=self.user,
            contest=self.contest,
            notebook=self.notebook
        )
        
        submissions = list(NotebookSubmission.objects.all())
        # Most recent first
        self.assertEqual(submissions[0].id, sub2.id)
        self.assertEqual(submissions[1].id, sub1.id)
