from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
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
        self.assertEqual(snapshot['cpu_load_percent'], 0.0)
        self.assertEqual(snapshot['gpu_load_percent'], 0.0)
