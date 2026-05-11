from time import perf_counter

from .services.request_metrics import record_request


class RequestMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            record_request(
                request.path,
                500,
                (perf_counter() - started_at) * 1000,
                method=request.method,
            )
            raise

        record_request(
            request.path,
            response.status_code,
            (perf_counter() - started_at) * 1000,
            method=request.method,
        )
        return response
