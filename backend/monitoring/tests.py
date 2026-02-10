from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from runner.models.submission import Submission
from runner.models.problem import Problem
from datetime import datetime, timedelta
import json


class MonitoringTestCase(TestCase):
    def setUp(self):
        # Create a test admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create a regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        
        # Create a test problem
        self.problem = Problem.objects.create(
            title="Test Problem",
            description="Test Description",
            author=self.admin_user
        )
        
        # Create some test submissions
        for i in range(5):
            Submission.objects.create(
                user=self.regular_user,
                problem=self.problem,
                status='accepted' if i % 2 == 0 else 'pending',
            )
        
        self.client = Client()

    def test_system_metrics_unauthorized_access(self):
        """Test that unauthorized users cannot access system metrics"""
        response = self.client.get(reverse('system-metrics'))
        self.assertEqual(response.status_code, 401)  # Unauthorized

    def test_system_metrics_regular_user_access(self):
        """Test that regular users cannot access system metrics"""
        self.client.login(username='regular', password='regularpass123')
        response = self.client.get(reverse('system-metrics'))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_system_metrics_admin_access(self):
        """Test that admin users can access system metrics"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('system-metrics'))
        self.assertEqual(response.status_code, 200)  # OK
        # Check that response contains expected metrics
        data = json.loads(response.content)
        self.assertIn('cpu', data)
        self.assertIn('memory', data)
        self.assertIn('disk', data)
        self.assertIn('timestamp', data)

    def test_task_statistics_admin_access(self):
        """Test that admin users can access task statistics"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('task-statistics'))
        self.assertEqual(response.status_code, 200)  # OK
        # Check that response contains expected statistics
        data = json.loads(response.content)
        self.assertIn('total', data)
        self.assertIn('pending', data)
        self.assertIn('running', data)
        self.assertIn('accepted', data)
        self.assertIn('failed', data)
        # Verify counts are correct
        self.assertEqual(data['total'], 5)
        self.assertEqual(data['pending'], 3)  # 3 out of 5 are pending (odd indices)
        self.assertEqual(data['accepted'], 2)  # 2 out of 5 are accepted (even indices)

    def test_historical_statistics_admin_access(self):
        """Test that admin users can access historical statistics"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('historical-statistics'))
        self.assertEqual(response.status_code, 200)  # OK
        # Check that response contains expected historical data
        data = json.loads(response.content)
        self.assertIn('daily', data)
        self.assertIn('weekly', data)
        self.assertIn('monthly', data)
        # Verify daily stats structure
        self.assertIn('total', data['daily'])
        self.assertIn('pending', data['daily'])
        self.assertIn('running', data['daily'])
        self.assertIn('accepted', data['daily'])
        self.assertIn('failed', data['daily'])