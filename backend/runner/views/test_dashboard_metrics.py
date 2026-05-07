from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from unittest.mock import patch

User = get_user_model()


class DashboardMetricsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPass123',
        )
        self.user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='StudentPass123',
        )
        self.metrics_url = reverse('runner:backend_request_metrics')
        self.ping_url = reverse('runner:backend_ping')
        self.check_auth_url = reverse('runner:backend_check_auth')

    def test_metrics_endpoint_requires_platform_admin(self):
        self.client.login(username='student', password='StudentPass123')

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 403)

    @patch('runner.views.dashboard_metrics.build_request_metrics_payload')
    def test_metrics_endpoint_reports_prometheus_payload(self, build_request_metrics_payload):
        build_request_metrics_payload.return_value = {
            'collector_mode': 'prometheus',
            'generated_at': '2026-05-07T09:00:00+00:00',
            'source': 'django-prometheus + Prometheus',
            'ranges': {
                '24h': {
                    'granularity': 'hour',
                    'points': [],
                    'summary': {
                        'ping_requests': 3,
                        'user_requests': 12,
                        'total_requests': 15,
                        'error_requests': 1,
                    },
                },
            },
        }
        self.client.login(username='admin', password='AdminPass123')

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 200)
        summary = response.data['ranges']['24h']['summary']
        self.assertEqual(summary['ping_requests'], 3)
        self.assertEqual(summary['user_requests'], 12)
        self.assertEqual(summary['total_requests'], 15)
        self.assertEqual(summary['error_requests'], 1)

    @patch('runner.views.dashboard_metrics.build_request_metrics_payload', side_effect=RuntimeError('Prometheus недоступен.'))
    def test_metrics_endpoint_returns_503_when_prometheus_unavailable(self, _build_request_metrics_payload):
        self.client.login(username='admin', password='AdminPass123')

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['detail'], 'Prometheus недоступен.')

    def test_ping_endpoint_is_public(self):
        response = self.client.get(self.ping_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ok')
