import shutil
import tempfile

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory
from unittest.mock import patch

from .receive_test_result import receive_test_result
from ..models.report import Report


class ReceiveTestResultViewTests(TestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self._media_root = tempfile.mkdtemp()
        self._override_media = override_settings(MEDIA_ROOT=self._media_root)
        self._override_media.enable()

    def tearDown(self) -> None:
        self._override_media.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def test_successful_report_creation_returns_serialized_response(self) -> None:
        payload = {
            "metric": 0.9,
            "log": "passed",
            "errors": "",
            "file_name": "submission.csv",
            "status": "success",
        }
        report = Report.objects.create(**payload)

        with patch("runner.views.receive_test_result.ReportGenerator") as mock_generator_class:
            mock_generator = mock_generator_class.return_value
            mock_generator.create_report_from_testing_system.return_value = report

            request = self.factory.post("/api/reports/create/", payload, format="json")
            response = receive_test_result(request)

        mock_generator.create_report_from_testing_system.assert_called_once_with(payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["file_name"], report.file_name)
        self.assertEqual(response.data["metric"], report.metric)
        self.assertEqual(response.data["status"], report.status)

    def test_creation_error_returns_bad_request(self) -> None:
        payload = {"metric": 0.3, "file_name": "broken.csv"}

        with patch("runner.views.receive_test_result.ReportGenerator") as mock_generator_class:
            mock_generator = mock_generator_class.return_value
            mock_generator.create_report_from_testing_system.side_effect = ValueError("boom")

            request = self.factory.post("/api/reports/create/", payload, format="json")
            response = receive_test_result(request)

        mock_generator.create_report_from_testing_system.assert_called_once_with(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Ошибка", response.data["error"])