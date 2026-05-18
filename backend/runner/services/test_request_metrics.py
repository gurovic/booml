from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from runner.models.notebook import Notebook
from runner.services import request_metrics
from runner.services.runtime import RuntimeSession, _sessions


User = get_user_model()


class RuntimeOverviewSnapshotTests(TestCase):
    def setUp(self):
        _sessions.clear()
        request_metrics._runtime_overview_cache_generated_at = None
        request_metrics._runtime_overview_cache_payload = None

    def tearDown(self):
        _sessions.clear()
        request_metrics._runtime_overview_cache_generated_at = None
        request_metrics._runtime_overview_cache_payload = None

    def test_counts_active_sessions_users_and_device_load(self):
        owner_a = User.objects.create_user(username='owner-a', password='test')
        owner_b = User.objects.create_user(username='owner-b', password='test')
        owner_a.profile.gpu_access = True
        owner_a.profile.save(update_fields=['gpu_access'])
        owner_b.profile.role = 'teacher'
        owner_b.profile.save(update_fields=['role'])

        cpu_notebook_a = Notebook.objects.create(owner=owner_a, title='CPU A', compute_device='cpu')
        gpu_notebook_a = Notebook.objects.create(owner=owner_a, title='GPU A', compute_device='gpu')
        cpu_notebook_b = Notebook.objects.create(owner=owner_b, title='CPU B', compute_device='cpu')

        now = timezone.now()
        cpu_vm = SimpleNamespace(spec=SimpleNamespace(gpu=False, resources=SimpleNamespace(cpu=2)))
        gpu_vm = SimpleNamespace(spec=SimpleNamespace(gpu=True, resources=SimpleNamespace(cpu=2)))

        _sessions[f'notebook:{cpu_notebook_a.id}'] = RuntimeSession({}, now, now, Path('/tmp/runtime-a'), None, cpu_vm)
        _sessions[f'notebook:{gpu_notebook_a.id}'] = RuntimeSession({}, now, now, Path('/tmp/runtime-b'), None, gpu_vm)
        _sessions[f'notebook:{cpu_notebook_b.id}'] = RuntimeSession({}, now, now, Path('/tmp/runtime-c'), None, cpu_vm)

        with patch.object(request_metrics, 'CPU_SESSION_CAPACITY', 4), patch.object(
            request_metrics,
            'GPU_SESSION_CAPACITY',
            2,
        ):
            snapshot = request_metrics._build_runtime_overview_snapshot()

        self.assertEqual(snapshot['active_sessions'], 3)
        self.assertEqual(snapshot['online_users'], 2)
        self.assertEqual(snapshot['online_users_by_role']['students'], 1)
        self.assertEqual(snapshot['online_users_by_role']['teachers'], 1)
        self.assertEqual(snapshot['online_users_by_role']['gpu_access'], 1)
        self.assertEqual(snapshot['cpu_load_percent'], 100.0)
        self.assertEqual(snapshot['gpu_load_percent'], 50.0)

    def test_filters_expired_sessions_out_of_snapshot(self):
        owner = User.objects.create_user(username='owner', password='test')
        notebook = Notebook.objects.create(owner=owner, title='Old CPU', compute_device='cpu')
        now = timezone.now()
        stale_time = now - timedelta(hours=2)
        cpu_vm = SimpleNamespace(spec=SimpleNamespace(gpu=False, resources=SimpleNamespace(cpu=2)))

        _sessions[f'notebook:{notebook.id}'] = RuntimeSession({}, stale_time, stale_time, Path('/tmp/runtime-old'), None, cpu_vm)

        snapshot = request_metrics._build_runtime_overview_snapshot()

        self.assertEqual(snapshot['active_sessions'], 0)
        self.assertEqual(snapshot['online_users'], 0)
        self.assertEqual(snapshot['online_users_by_role']['students'], 0)
        self.assertEqual(snapshot['online_users_by_role']['teachers'], 0)
        self.assertEqual(snapshot['online_users_by_role']['gpu_access'], 0)
        self.assertEqual(snapshot['cpu_load_percent'], 0.0)
        self.assertEqual(snapshot['gpu_load_percent'], 0.0)


class RequestMetricsPayloadTests(SimpleTestCase):
    def test_gauge_series_keep_peak_history_but_end_with_current_snapshot(self):
        step_interval = '1h'

        def fake_query_range(expression, *, points, **_kwargs):
            default = [0.0] * points

            if expression == request_metrics._counter_query(interval=step_interval, category='ping'):
                return [2.0] * points
            if expression == request_metrics._counter_query(interval=step_interval, category='user'):
                return [8.0] * points
            if expression == request_metrics._counter_query(interval=step_interval, errors_only=True):
                return default
            if expression == request_metrics._latency_average_query(interval=step_interval):
                return [16.0] * points
            if expression == request_metrics._latency_average_query(interval=step_interval, category='ping'):
                return [9.0] * points
            if expression == request_metrics._peak_gauge_query(
                request_metrics._metric_name('active_sessions'),
                interval=step_interval,
            ):
                return default[:-2] + [1.0, 1.0]
            if expression == request_metrics._peak_gauge_query(
                request_metrics._metric_name('online_users'),
                interval=step_interval,
            ):
                return default[:-2] + [1.0, 1.0]
            if expression == request_metrics._peak_gauge_query(
                request_metrics._metric_name('cpu_load_percent'),
                interval=step_interval,
            ):
                return default[:-2] + [40.0, 40.0]
            if expression == request_metrics._peak_gauge_query(
                request_metrics._metric_name('gpu_load_percent'),
                interval=step_interval,
            ):
                return default[:-2] + [80.0, 80.0]
            if expression == request_metrics._peak_gauge_query(
                request_metrics._metric_name('submission_queue_size'),
                interval=step_interval,
            ):
                return default[:-2] + [3.0, 3.0]
            if expression == request_metrics._peak_gauge_query(
                request_metrics._metric_name('submission_running_size'),
                interval=step_interval,
            ):
                return default[:-2] + [2.0, 2.0]
            return default

        def fake_query_instant(expression, *, at):
            del at
            if expression.startswith('avg_over_time('):
                return 0.0
            if expression.startswith('sum(increase('):
                return 24.0
            if 'request_latency_seconds' in expression and 'category="ping"' in expression:
                return 9.0
            if 'request_latency_seconds' in expression:
                return 16.0
            return 0.0

        with patch.object(
            request_metrics,
            '_build_runtime_overview_snapshot',
            return_value={
                'active_sessions': 0,
                'online_users': 0,
                'online_users_by_role': {
                    'students': 0,
                    'teachers': 0,
                    'gpu_access': 0,
                },
                'cpu_load_percent': 0.0,
                'gpu_load_percent': 0.0,
                'ram_used_gb': 0.0,
                'ram_total_gb': 32.0,
                'vram_used_gb': 0.0,
                'vram_total_gb': 24.0,
                'sessions': [],
                'session_cells_total': 0,
            },
        ), patch.object(request_metrics, '_query_range_values', side_effect=fake_query_range), patch.object(
            request_metrics,
            '_query_instant',
            side_effect=fake_query_instant,
        ), patch.object(
            request_metrics,
            '_build_submission_queue_snapshot',
            return_value={
                'pending': 0,
                'running': 0,
                'avg_wait_seconds': 0,
                'max_wait_seconds': 0,
            },
        ):
            payload = request_metrics.build_request_metrics_payload()

        cards = payload['ranges']['24h']['cards']
        self.assertEqual(cards['active_sessions']['value'], 0)
        self.assertEqual(cards['active_sessions']['points'][-2], 1)
        self.assertEqual(cards['active_sessions']['points'][-1], 0)
        self.assertEqual(cards['online_users']['value'], 0)
        self.assertEqual(cards['online_users']['points'][-2], 1)
        self.assertEqual(cards['online_users']['points'][-1], 0)
        self.assertEqual(cards['online_users']['by_role']['students'], 0)
        self.assertEqual(cards['online_users']['by_role']['teachers'], 0)
        self.assertEqual(cards['online_users']['by_role']['gpu_access'], 0)
        self.assertEqual(cards['cpu_gpu_load']['cpu_percent'], 0.0)
        self.assertEqual(cards['cpu_gpu_load']['gpu_percent'], 0.0)
        self.assertEqual(cards['cpu_gpu_load']['points'][-2], 60.0)
        self.assertEqual(cards['cpu_gpu_load']['points'][-1], 0.0)
        self.assertEqual(cards['submission_queue']['value'], 0)
        self.assertEqual(cards['submission_queue']['points'][-2], 3)
        self.assertEqual(cards['submission_queue']['points'][-1], 0)
        self.assertEqual(cards['submission_queue']['running_points'][-2], 2)
        self.assertEqual(cards['submission_queue']['running_points'][-1], 0)
