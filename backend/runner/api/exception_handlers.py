from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Ensure API errors are returned as JSON even for unexpected exceptions.
    """
    response = exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, ValueError):
        payload = {"message": "Ошибка в данных запроса."}
        if settings.DEBUG:
            payload["detail"] = str(exc)
        return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    payload = {"message": "Внутренняя ошибка сервера."}
    if settings.DEBUG:
        payload["detail"] = str(exc)
    return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
