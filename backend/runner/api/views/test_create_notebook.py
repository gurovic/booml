from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from runner.models import Notebook, Problem

User = get_user_model()


class CreateNotebookAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass123")
        self.client.login(username="testuser", password="pass123")
        self.problem = Problem.objects.create(title="Test Problem", statement="Test statement")
        self.create_url = reverse("notebook-create")

    def test_create_notebook_without_problem(self):
        """Test creating a notebook without a problem"""
        resp = self.client.post(self.create_url, {"title": "My Notebook"}, content_type="application/json")
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["title"], "My Notebook")
        self.assertIsNone(data["problem_id"])
        
        # Verify notebook was created
        notebook = Notebook.objects.get(pk=data["id"])
        self.assertEqual(notebook.owner, self.user)
        self.assertEqual(notebook.title, "My Notebook")
        self.assertIsNone(notebook.problem)

    def test_create_notebook_with_problem(self):
        """Test creating a notebook for a problem"""
        resp = self.client.post(
            self.create_url, 
            {"problem_id": self.problem.id},
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["problem_id"], self.problem.id)
        self.assertIn("Test Problem", data["title"])
        
        # Verify notebook was created with problem association
        notebook = Notebook.objects.get(pk=data["id"])
        self.assertEqual(notebook.owner, self.user)
        self.assertEqual(notebook.problem, self.problem)

    def test_create_duplicate_notebook_for_problem(self):
        """Test that creating a second notebook for the same problem returns the existing one"""
        # Create first notebook
        resp1 = self.client.post(
            self.create_url,
            {"problem_id": self.problem.id},
            content_type="application/json"
        )
        self.assertEqual(resp1.status_code, HTTPStatus.CREATED)
        data1 = resp1.json()
        notebook_id = data1["id"]
        
        # Try to create second notebook for the same problem
        resp2 = self.client.post(
            self.create_url,
            {"problem_id": self.problem.id},
            content_type="application/json"
        )
        self.assertEqual(resp2.status_code, HTTPStatus.OK)
        data2 = resp2.json()
        
        # Should return the same notebook
        self.assertEqual(data2["id"], notebook_id)
        self.assertIn("already exists", data2.get("message", ""))
        
        # Verify only one notebook was created
        notebook_count = Notebook.objects.filter(owner=self.user, problem=self.problem).count()
        self.assertEqual(notebook_count, 1)

    def test_create_notebook_requires_authentication(self):
        """Test that creating a notebook requires authentication"""
        self.client.logout()
        resp = self.client.post(
            self.create_url,
            {"problem_id": self.problem.id},
            content_type="application/json"
        )
        # Should return 403 Forbidden or 401 Unauthorized
        self.assertIn(resp.status_code, [HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED])

    def test_create_notebook_with_invalid_problem(self):
        """Test creating a notebook with a non-existent problem"""
        resp = self.client.post(
            self.create_url,
            {"problem_id": 9999},
            content_type="application/json"
        )
        # Serializer validation returns 400 BAD_REQUEST for invalid problem_id
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
