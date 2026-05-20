import time

from .services.request_metrics import record_request


class RequestMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        record_request(
            path=request.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            method=request.method,
        )
        return response
