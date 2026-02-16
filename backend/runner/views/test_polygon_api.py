from django.contrib.auth import get_user_model
from django.test import TestCase
import json

from ..models.problem import Problem

User = get_user_model()


class PolygonProblemsApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="author", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.url = "/backend/polygon/problems"

        # Create problems for different users
        self.problem1 = Problem.objects.create(
            title="My Problem 1",
            author=self.user,
            is_published=True,
            rating=1000
        )
        self.problem2 = Problem.objects.create(
            title="My Problem 2",
            author=self.user,
            is_published=False,
            rating=1500
        )
        self.other_problem = Problem.objects.create(
            title="Other Problem",
            author=self.other_user,
            is_published=True,
            rating=2000
        )
        self.other_draft = Problem.objects.create(
            title="Other Draft",
            author=self.other_user,
            is_published=False,
            rating=2100
        )

    def test_list_requires_authentication(self):
        """Test that listing problems requires authentication"""
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_list_returns_only_user_problems(self):
        """Test that list returns own problems + other users' published problems"""
        self.client.login(username="author", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        
        data = resp.json()
        self.assertEqual(len(data), 3)
        
        problem_ids = [p['id'] for p in data]
        self.assertIn(self.problem1.id, problem_ids)
        self.assertIn(self.problem2.id, problem_ids)
        self.assertIn(self.other_problem.id, problem_ids)
        self.assertNotIn(self.other_draft.id, problem_ids)

    def test_list_includes_all_fields(self):
        """Test that list includes required fields"""
        self.client.login(username="author", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        
        data = resp.json()
        self.assertGreater(len(data), 0)
        
        problem = data[0]
        self.assertIn('id', problem)
        self.assertIn('title', problem)
        self.assertIn('rating', problem)
        self.assertIn('is_published', problem)
        self.assertIn('author_username', problem)
        self.assertIn('created_at', problem)

    def test_search_filters_by_title(self):
        self.client.login(username="author", password="pass")
        resp = self.client.get(self.url, {"q": "Other"})
        self.assertEqual(resp.status_code, 200)

        payload = resp.json()
        items = payload.get("items", []) if isinstance(payload, dict) else payload
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], self.other_problem.id)


class CreatePolygonProblemApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="creator", password="pass")
        self.url = "/backend/polygon/problems/create"

    def test_create_requires_authentication(self):
        """Test that creating a problem requires authentication"""
        self.client.logout()
        resp = self.client.post(
            self.url,
            data=json.dumps({"title": "Test"}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)

    def test_create_minimal_problem(self):
        """Test creating a problem with minimal data"""
        self.client.login(username="creator", password="pass")
        resp = self.client.post(
            self.url,
            data=json.dumps({"title": "New Problem"}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)
        
        data = resp.json()
        self.assertEqual(data['title'], "New Problem")
        self.assertEqual(data['rating'], 800)  # Default rating
        
        # Verify problem was created in database
        problem = Problem.objects.get(id=data['id'])
        self.assertEqual(problem.author, self.user)
        self.assertFalse(problem.is_published)  # Should be unpublished by default

    def test_create_with_rating(self):
        """Test creating a problem with custom rating"""
        self.client.login(username="creator", password="pass")
        resp = self.client.post(
            self.url,
            data=json.dumps({"title": "Hard Problem", "rating": 2500}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)
        
        data = resp.json()
        self.assertEqual(data['rating'], 2500)

    def test_create_requires_title(self):
        """Test that title is required"""
        self.client.login(username="creator", password="pass")
        resp = self.client.post(
            self.url,
            data=json.dumps({"rating": 1000}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_rejects_empty_title(self):
        """Test that empty title is rejected"""
        self.client.login(username="creator", password="pass")
        resp = self.client.post(
            self.url,
            data=json.dumps({"title": "   "}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
