from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView


class _ValueErrorView(APIView):
    def get(self, request):
        raise ValueError("boom")


class _RuntimeErrorView(APIView):
    def get(self, request):
        raise RuntimeError("boom")


class ExceptionHandlerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_value_error_returns_json_400(self):
        request = self.factory.get("/api/test-value-error/")
        response = _ValueErrorView.as_view()(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("message"), "Ошибка в данных запроса.")

    def test_unexpected_error_returns_json_500(self):
        request = self.factory.get("/api/test-runtime-error/")
        response = _RuntimeErrorView.as_view()(request)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.get("message"), "Внутренняя ошибка сервера.")
