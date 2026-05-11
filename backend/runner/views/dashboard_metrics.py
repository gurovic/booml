from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..services.request_metrics import build_request_metrics_payload
from ..services.user_access import is_platform_admin


def _can_access_dashboard_metrics(user) -> bool:
    return bool(
        getattr(user, 'is_authenticated', False)
        and (is_platform_admin(user) or getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False))
    )


@api_view(['GET'])
def backend_ping(request):
    return Response({'status': 'ok'})


@api_view(['GET'])
def backend_request_metrics(request):
    if not _can_access_dashboard_metrics(request.user):
        return Response(
            {'detail': 'Only platform admins can access dashboard metrics.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        return Response(build_request_metrics_payload())
    except RuntimeError as exc:
        return Response(
            {'detail': str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
