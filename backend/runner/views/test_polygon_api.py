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


class GetPolygonProblemApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        
        self.problem = Problem.objects.create(
            title="Test Problem",
            author=self.user,
            rating=1200,
            statement="Test statement",
            is_published=False
        )
        
        self.url = f"/backend/polygon/problems/{self.problem.id}"
    
    def test_get_requires_authentication(self):
        """Test that getting problem details requires authentication"""
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)
    
    def test_get_own_problem(self):
        """Test that owner can get their own problem"""
        self.client.login(username="owner", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        
        data = resp.json()
        self.assertEqual(data['id'], self.problem.id)
        self.assertEqual(data['title'], self.problem.title)
        self.assertEqual(data['rating'], self.problem.rating)
        self.assertEqual(data['statement'], self.problem.statement)
        self.assertIn('descriptor', data)
        self.assertIn('files', data)
        self.assertIn('available_metrics', data)
    
    def test_get_others_problem_forbidden(self):
        """Test that user cannot get another user's problem"""
        self.client.login(username="other", password="pass")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 404)


class UpdatePolygonProblemApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        
        self.problem = Problem.objects.create(
            title="Original Title",
            author=self.user,
            rating=1000,
            statement="Original statement",
            is_published=False
        )
        
        self.url = f"/backend/polygon/problems/{self.problem.id}/update"
    
    def test_update_requires_authentication(self):
        """Test that updating problem requires authentication"""
        self.client.logout()
        resp = self.client.put(
            self.url,
            data=json.dumps({"title": "New Title"}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)
    
    def test_update_basic_fields(self):
        """Test updating basic problem fields"""
        self.client.login(username="owner", password="pass")
        resp = self.client.put(
            self.url,
            data=json.dumps({
                "title": "Updated Title",
                "rating": 1500,
                "statement": "Updated statement"
            }),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        
        # Verify changes in database
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.title, "Updated Title")
        self.assertEqual(self.problem.rating, 1500)
        self.assertEqual(self.problem.statement, "Updated statement")
    
    def test_update_validates_rating(self):
        """Test that rating is validated"""
        self.client.login(username="owner", password="pass")
        resp = self.client.put(
            self.url,
            data=json.dumps({"rating": 5000}),  # Out of range
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('errors', data)


class PublishPolygonProblemApiTests(TestCase):
    def setUp(self):
        from ..models.problem_desriptor import ProblemDescriptor
        from ..models.problem_data import ProblemData
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        self.user = User.objects.create_user(username="owner", password="pass")
        
        self.problem = Problem.objects.create(
            title="Complete Problem",
            author=self.user,
            rating=1000,
            statement="Complete statement",
            is_published=False
        )
        
        # Create descriptor
        ProblemDescriptor.objects.create(
            problem=self.problem,
            id_column="id",
            target_column="target",
            id_type="int",
            target_type="float",
            metric_name="rmse"
        )
        
        # Create answer file
        answer_file = SimpleUploadedFile("answer.csv", b"id,target\n1,0.5\n", content_type="text/csv")
        ProblemData.objects.create(
            problem=self.problem,
            answer_file=answer_file
        )
        
        self.url = f"/backend/polygon/problems/{self.problem.id}/publish"
    
    def test_publish_requires_authentication(self):
        """Test that publishing requires authentication"""
        self.client.logout()
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 401)
    
    def test_publish_complete_problem(self):
        """Test publishing a complete problem"""
        self.client.login(username="owner", password="pass")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        
        # Verify problem is published
        self.problem.refresh_from_db()
        self.assertTrue(self.problem.is_published)
    
    def test_publish_incomplete_problem_fails(self):
        """Test that incomplete problem cannot be published"""
        # Create incomplete problem (no descriptor)
        incomplete = Problem.objects.create(
            title="Incomplete",
            author=self.user,
            rating=1000,
            is_published=False
        )
        
        self.client.login(username="owner", password="pass")
        resp = self.client.post(f"/backend/polygon/problems/{incomplete.id}/publish")
        self.assertEqual(resp.status_code, 400)
        
        data = resp.json()
        self.assertIn('errors', data)
        
        # Verify problem is not published
        incomplete.refresh_from_db()
        self.assertFalse(incomplete.is_published)
