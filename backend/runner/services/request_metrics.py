from __future__ import annotations

import datetime as dt
import os
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.utils import timezone
from prometheus_client import Counter, Gauge, Histogram

PING_PATH_PREFIXES = (
    '/backend/ping/',
    '/api/ping/',
    '/ping/',
    '/health/',
    '/healthz/',
    '/ready/',
    '/readyz/',
    '/live/',
    '/livez/',
)

IGNORED_PATH_PREFIXES = (
    '/static/',
    '/media/',
    '/admin/',
)

IGNORED_EXACT_PATHS = frozenset({
    '/backend/dashboard/request-metrics/',
    '/prometheus/metrics/',
})

METRIC_NAMESPACE = getattr(settings, 'PROMETHEUS_METRIC_NAMESPACE', 'booml')
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://127.0.0.1:9090').rstrip('/')
PROMETHEUS_TIMEOUT_SECONDS = float(os.getenv('PROMETHEUS_TIMEOUT_SECONDS', '5'))
NOTEBOOK_SESSION_PREFIX = 'notebook:'
CPU_SESSION_CAPACITY = max(1, int(os.getenv('DASHBOARD_CPU_SESSION_CAPACITY', str(os.cpu_count() or 8))))
GPU_SESSION_CAPACITY = max(1, int(os.getenv('DASHBOARD_GPU_SESSION_CAPACITY', '1')))
DEFAULT_SESSION_CPU = max(1, int(getattr(settings, 'RUNTIME_VM_CPU', 2)))
_RUNTIME_OVERVIEW_CACHE_TTL_SECONDS = 5
_runtime_overview_cache_generated_at: dt.datetime | None = None
_runtime_overview_cache_payload: dict[str, float | int] | None = None

REQUEST_COUNTER = Counter(
    'http_requests',
    'HTTP requests grouped for dashboard traffic analysis.',
    labelnames=('category', 'method', 'status'),
    namespace=METRIC_NAMESPACE,
    subsystem='backend',
)

REQUEST_LATENCY = Histogram(
    'request_latency_seconds',
    'Observed backend request latency in seconds.',
    labelnames=('category', 'method'),
    namespace=METRIC_NAMESPACE,
    subsystem='backend',
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_SESSIONS_GAUGE = Gauge(
    'active_sessions',
    'Current number of active notebook runtime sessions.',
    namespace=METRIC_NAMESPACE,
    subsystem='backend',
)

ONLINE_USERS_GAUGE = Gauge(
    'online_users',
    'Current number of distinct users with active notebook runtime sessions.',
    namespace=METRIC_NAMESPACE,
    subsystem='backend',
)

CPU_LOAD_PERCENT_GAUGE = Gauge(
    'cpu_load_percent',
    'Approximate CPU load derived from active CPU runtime sessions.',
    namespace=METRIC_NAMESPACE,
    subsystem='backend',
)

GPU_LOAD_PERCENT_GAUGE = Gauge(
    'gpu_load_percent',
    'Approximate GPU load derived from active GPU runtime sessions.',
    namespace=METRIC_NAMESPACE,
    subsystem='backend',
)

RANGE_CONFIG = {
    '24h': {
        'granularity': 'hour',
        'points': 24,
        'step': dt.timedelta(hours=1),
    },
    '7d': {
        'granularity': 'day',
        'points': 7,
        'step': dt.timedelta(days=1),
    },
    '30d': {
        'granularity': 'day',
        'points': 30,
        'step': dt.timedelta(days=1),
    },
}


def _canonical_path(path: str | None) -> str:
    if not path:
        return '/'
    if not path.startswith('/'):
        path = f'/{path}'
    if path != '/' and not path.endswith('/'):
        path = f'{path}/'
    return path


def _should_track_path(path: str) -> bool:
    if path in IGNORED_EXACT_PATHS:
        return False
    return not any(path.startswith(prefix) for prefix in IGNORED_PATH_PREFIXES)


def _is_ping_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in PING_PATH_PREFIXES)


def _categorize_path(path: str) -> str:
    return 'ping' if _is_ping_path(path) else 'user'


def _metric_name(metric: str) -> str:
    return f'{METRIC_NAMESPACE}_backend_{metric}'


def _session_ttl_seconds() -> int:
    try:
        return max(0, int(getattr(settings, 'RUNTIME_SESSION_TTL_SECONDS', 3600)))
    except (TypeError, ValueError):
        return 3600


def _normalize_datetime(value: dt.datetime | None) -> dt.datetime:
    resolved = value or timezone.now()
    if timezone.is_naive(resolved):
        return timezone.make_aware(resolved, timezone.get_current_timezone())
    return resolved


def _extract_notebook_id(session_id: str) -> int | None:
    if not session_id.startswith(NOTEBOOK_SESSION_PREFIX):
        return None

    suffix = session_id[len(NOTEBOOK_SESSION_PREFIX):]
    return int(suffix) if suffix.isdigit() else None


def _clamp_percent(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 1)


def _build_runtime_overview_snapshot() -> dict[str, float | int]:
    global _runtime_overview_cache_generated_at, _runtime_overview_cache_payload

    now = timezone.now()
    if (
        _runtime_overview_cache_generated_at is not None
        and _runtime_overview_cache_payload is not None
        and (now - _runtime_overview_cache_generated_at).total_seconds() < _RUNTIME_OVERVIEW_CACHE_TTL_SECONDS
    ):
        return _runtime_overview_cache_payload

    try:
        from ..models.notebook import Notebook
        from .runtime import _sessions
    except Exception:
        snapshot = {
            'active_sessions': 0,
            'online_users': 0,
            'cpu_load_percent': 0.0,
            'gpu_load_percent': 0.0,
        }
        _runtime_overview_cache_generated_at = now
        _runtime_overview_cache_payload = snapshot
        return snapshot

    cutoff = now - dt.timedelta(seconds=_session_ttl_seconds())
    active_sessions: list[tuple[int, object]] = []
    notebook_ids: set[int] = set()

    for session_id, session in list(_sessions.items()):
        notebook_id = _extract_notebook_id(session_id)
        if notebook_id is None:
            continue

        updated_at = _normalize_datetime(getattr(session, 'updated_at', None))
        if updated_at < cutoff:
            continue

        active_sessions.append((notebook_id, session))
        notebook_ids.add(notebook_id)

    notebooks = Notebook.objects.filter(id__in=notebook_ids).values('id', 'owner_id', 'compute_device')
    notebooks_by_id = {notebook['id']: notebook for notebook in notebooks}

    online_user_ids: set[int] = set()
    cpu_sessions = 0
    gpu_sessions = 0
    cpu_reserved = 0

    for notebook_id, session in active_sessions:
        notebook = notebooks_by_id.get(notebook_id)
        owner_id = notebook.get('owner_id') if notebook else None
        if owner_id is not None:
            online_user_ids.add(owner_id)

        vm = getattr(session, 'vm', None)
        vm_spec = getattr(vm, 'spec', None)
        vm_resources = getattr(vm_spec, 'resources', None)
        is_gpu = bool(getattr(vm_spec, 'gpu', False)) if vm_spec is not None else (notebook or {}).get('compute_device') == 'gpu'

        if is_gpu:
            gpu_sessions += 1
            continue

        cpu_sessions += 1
        cpu_reserved += max(1, int(getattr(vm_resources, 'cpu', DEFAULT_SESSION_CPU)))

    snapshot = {
        'active_sessions': len(active_sessions),
        'online_users': len(online_user_ids),
        'cpu_load_percent': _clamp_percent((cpu_reserved / CPU_SESSION_CAPACITY) * 100),
        'gpu_load_percent': _clamp_percent((gpu_sessions / GPU_SESSION_CAPACITY) * 100),
    }

    _runtime_overview_cache_generated_at = now
    _runtime_overview_cache_payload = snapshot
    return snapshot


def _format_prometheus_duration(delta: dt.timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds % 86400 == 0:
        return f'{total_seconds // 86400}d'
    if total_seconds % 3600 == 0:
        return f'{total_seconds // 3600}h'
    if total_seconds % 60 == 0:
        return f'{total_seconds // 60}m'
    return f'{total_seconds}s'


def _query_selector(*matchers: str) -> str:
    clean_matchers = [matcher for matcher in matchers if matcher]
    if not clean_matchers:
        return ''
    return '{' + ','.join(clean_matchers) + '}'


def _counter_query(*, interval: str, category: str | None = None, errors_only: bool = False) -> str:
    selector = _query_selector(
        f'category="{category}"' if category else '',
        'status=~"5.."' if errors_only else '',
    )
    return f'sum(increase({_metric_name("http_requests_total")}{selector}[{interval}]))'


def _latency_average_query(*, interval: str, category: str | None = None) -> str:
    selector = _query_selector(f'category="{category}"' if category else '')
    sum_expr = f'sum(increase({_metric_name("request_latency_seconds_sum")}{selector}[{interval}]))'
    count_expr = f'sum(increase({_metric_name("request_latency_seconds_count")}{selector}[{interval}]))'
    return f'((1000 * {sum_expr}) / clamp_min({count_expr}, 1)) or vector(0)'


def _average_gauge_query(metric: str, *, interval: str) -> str:
    return f'avg_over_time({metric}[{interval}])'


def _to_float(value) -> float:
    if value in (None, '', 'NaN', 'nan'):
        return 0.0
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return 0.0


def _perform_query(endpoint: str, *, params: dict[str, str]) -> dict:
    try:
        response = requests.get(
            f'{PROMETHEUS_URL}/api/v1/{endpoint}',
            params=params,
            timeout=PROMETHEUS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError('Не удалось получить данные из Prometheus.') from exc

    payload = response.json()
    if payload.get('status') != 'success':
        raise RuntimeError('Prometheus вернул ошибку при запросе метрик.')
    return payload.get('data', {})


def _query_instant(expression: str, *, at: dt.datetime) -> float:
    data = _perform_query(
        'query',
        params={
            'query': expression,
            'time': at.isoformat(),
        },
    )
    result = data.get('result') or []
    if not result:
        return 0.0
    return _to_float(result[0].get('value', [None, 0])[1])


def _query_range_values(expression: str, *, start: dt.datetime, end: dt.datetime, step: dt.timedelta, points: int) -> list[float]:
    data = _perform_query(
        'query_range',
        params={
            'query': expression,
            'start': start.isoformat(),
            'end': end.isoformat(),
            'step': _format_prometheus_duration(step),
        },
    )
    result = data.get('result') or []
    if not result:
        return [0.0] * points

    values = [_to_float(value[1]) for value in result[0].get('values', [])]
    if len(values) < points:
        values = ([0.0] * (points - len(values))) + values
    if len(values) > points:
        values = values[-points:]
    return values


def _compute_trend(current_value: float, previous_value: float) -> float | None:
    if previous_value <= 0:
        return None
    return round(((current_value - previous_value) / previous_value) * 100, 1)


def _build_timestamps(end: dt.datetime, *, step: dt.timedelta, points: int) -> list[dt.datetime]:
    start = end - step * (points - 1)
    return [start + step * index for index in range(points)]


def record_request(path: str, status_code: int, duration_ms: float, *, method: str = 'GET') -> None:
    if str(method).upper() == 'OPTIONS':
        return

    normalized_path = _canonical_path(path)
    if not _should_track_path(normalized_path):
        return

    category = _categorize_path(normalized_path)
    request_method = str(method or 'GET').upper()
    status = str(int(status_code))

    REQUEST_COUNTER.labels(category=category, method=request_method, status=status).inc()
    REQUEST_LATENCY.labels(category=category, method=request_method).observe(max(float(duration_ms), 0.0) / 1000)


def build_request_metrics_payload() -> dict[str, object]:
    generated_at = timezone.now().astimezone(dt.timezone.utc)
    runtime_snapshot = _build_runtime_overview_snapshot()
    ranges: dict[str, object] = {}

    for range_key, config in RANGE_CONFIG.items():
        step: dt.timedelta = config['step']
        points_count: int = config['points']
        window = step * points_count
        step_interval = _format_prometheus_duration(step)
        window_interval = _format_prometheus_duration(window)
        previous_end = generated_at - window

        timestamps = _build_timestamps(generated_at, step=step, points=points_count)
        ping_values = _query_range_values(
            _counter_query(interval=step_interval, category='ping'),
            start=timestamps[0],
            end=generated_at,
            step=step,
            points=points_count,
        )
        user_values = _query_range_values(
            _counter_query(interval=step_interval, category='user'),
            start=timestamps[0],
            end=generated_at,
            step=step,
            points=points_count,
        )
        error_values = _query_range_values(
            _counter_query(interval=step_interval, errors_only=True),
            start=timestamps[0],
            end=generated_at,
            step=step,
            points=points_count,
        )
        avg_duration_values = _query_range_values(
            _latency_average_query(interval=step_interval),
            start=timestamps[0],
            end=generated_at,
            step=step,
            points=points_count,
        )
        avg_ping_values = _query_range_values(
            _latency_average_query(interval=step_interval, category='ping'),
            start=timestamps[0],
            end=generated_at,
            step=step,
            points=points_count,
        )
        active_session_values = _query_range_values(
            _metric_name('active_sessions'),
            start=timestamps[0],
            end=generated_at,
            step=step,
            points=points_count,
        )
        online_user_values = _query_range_values(
            _metric_name('online_users'),
            start=timestamps[0],
            end=generated_at,
            step=step,
            points=points_count,
        )
        cpu_load_values = _query_range_values(
            _metric_name('cpu_load_percent'),
            start=timestamps[0],
            end=generated_at,
            step=step,
            points=points_count,
        )
        gpu_load_values = _query_range_values(
            _metric_name('gpu_load_percent'),
            start=timestamps[0],
            end=generated_at,
            step=step,
            points=points_count,
        )

        points = []
        for index, timestamp in enumerate(timestamps):
            ping_requests = int(round(ping_values[index]))
            user_requests = int(round(user_values[index]))
            error_requests = int(round(error_values[index]))
            points.append({
                'timestamp': timestamp.isoformat(),
                'total_requests': ping_requests + user_requests,
                'ping_requests': ping_requests,
                'user_requests': user_requests,
                'error_requests': error_requests,
                'avg_duration_ms': round(avg_duration_values[index], 1),
                'avg_ping_ms': round(avg_ping_values[index], 1),
            })

        total_requests = int(round(_query_instant(_counter_query(interval=window_interval), at=generated_at)))
        ping_requests = int(round(_query_instant(_counter_query(interval=window_interval, category='ping'), at=generated_at)))
        user_requests = int(round(_query_instant(_counter_query(interval=window_interval, category='user'), at=generated_at)))
        error_requests = int(round(_query_instant(_counter_query(interval=window_interval, errors_only=True), at=generated_at)))
        previous_total = int(round(_query_instant(_counter_query(interval=window_interval), at=previous_end)))
        avg_duration_ms = round(_query_instant(_latency_average_query(interval=window_interval), at=generated_at), 1)
        avg_ping_ms = round(_query_instant(_latency_average_query(interval=window_interval, category='ping'), at=generated_at), 1)
        trend_percent = _compute_trend(total_requests, previous_total)
        active_sessions_current = int(round(float(runtime_snapshot['active_sessions'])))
        online_users_current = int(round(float(runtime_snapshot['online_users'])))
        cpu_load_current = round(float(runtime_snapshot['cpu_load_percent']), 1)
        gpu_load_current = round(float(runtime_snapshot['gpu_load_percent']), 1)
        active_sessions_trend = _compute_trend(
            _query_instant(_average_gauge_query(_metric_name('active_sessions'), interval=window_interval), at=generated_at),
            _query_instant(_average_gauge_query(_metric_name('active_sessions'), interval=window_interval), at=previous_end),
        )
        online_users_trend = _compute_trend(
            _query_instant(_average_gauge_query(_metric_name('online_users'), interval=window_interval), at=generated_at),
            _query_instant(_average_gauge_query(_metric_name('online_users'), interval=window_interval), at=previous_end),
        )
        cpu_load_average = _query_instant(_average_gauge_query(_metric_name('cpu_load_percent'), interval=window_interval), at=generated_at)
        cpu_load_average_previous = _query_instant(
            _average_gauge_query(_metric_name('cpu_load_percent'), interval=window_interval),
            at=previous_end,
        )
        gpu_load_average = _query_instant(_average_gauge_query(_metric_name('gpu_load_percent'), interval=window_interval), at=generated_at)
        gpu_load_average_previous = _query_instant(
            _average_gauge_query(_metric_name('gpu_load_percent'), interval=window_interval),
            at=previous_end,
        )
        combined_load_trend = _compute_trend(
            (cpu_load_average + gpu_load_average) / 2,
            (cpu_load_average_previous + gpu_load_average_previous) / 2,
        )
        combined_load_points = [
            round((cpu_load_values[index] + gpu_load_values[index]) / 2, 1)
            for index in range(points_count)
        ]

        ranges[range_key] = {
            'granularity': config['granularity'],
            'points': points,
            'cards': {
                'active_sessions': {
                    'value': active_sessions_current,
                    'trend_percent': active_sessions_trend,
                    'points': [int(round(value)) for value in active_session_values],
                },
                'server_requests': {
                    'value': total_requests,
                    'trend_percent': trend_percent,
                    'points': [point['total_requests'] for point in points],
                },
                'cpu_gpu_load': {
                    'cpu_percent': cpu_load_current,
                    'gpu_percent': gpu_load_current,
                    'trend_percent': combined_load_trend,
                    'points': combined_load_points,
                },
                'online_users': {
                    'value': online_users_current,
                    'trend_percent': online_users_trend,
                    'points': [int(round(value)) for value in online_user_values],
                },
            },
            'summary': {
                'total_requests': total_requests,
                'ping_requests': ping_requests,
                'user_requests': user_requests,
                'error_requests': error_requests,
                'error_rate': round((error_requests / total_requests) * 100, 2) if total_requests else 0.0,
                'avg_duration_ms': avg_duration_ms,
                'avg_ping_ms': avg_ping_ms,
                'peak_requests': max((point['total_requests'] for point in points), default=0),
                'trend_percent': trend_percent,
            },
        }

    return {
        'collector_mode': 'prometheus',
        'collector_started_at': None,
        'generated_at': generated_at.isoformat(),
        'source': 'django-prometheus + Prometheus',
        'ranges': ranges,
    }


ACTIVE_SESSIONS_GAUGE.set_function(lambda: float(_build_runtime_overview_snapshot()['active_sessions']))
ONLINE_USERS_GAUGE.set_function(lambda: float(_build_runtime_overview_snapshot()['online_users']))
CPU_LOAD_PERCENT_GAUGE.set_function(lambda: float(_build_runtime_overview_snapshot()['cpu_load_percent']))
GPU_LOAD_PERCENT_GAUGE.set_function(lambda: float(_build_runtime_overview_snapshot()['gpu_load_percent']))
