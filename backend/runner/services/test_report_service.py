from django.core.exceptions import ValidationError
import shutil
import tempfile

from django.test import TestCase, override_settings
from unittest.mock import patch

from .report_service import ReportGenerator
from ..models.report import Report


class ReportGeneratorTests(TestCase):
    def setUp(self) -> None:
        self.generator = ReportGenerator()
        self._media_root = tempfile.mkdtemp()
        self._override_media = override_settings(MEDIA_ROOT=self._media_root)
        self._override_media.enable()

    def tearDown(self) -> None:
        self._override_media.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def test_creates_report_from_valid_payload(self) -> None:
        payload = {
            "metric": "0.92",
            "log": "all good",
            "errors": "",
            "file_name": "results.csv",
            "test_data": {"submission_id": 1},
        }

        report = self.generator.create_report_from_testing_system(payload)

        self.assertIsInstance(report, Report)
        self.assertAlmostEqual(report.metric, 0.92)
        self.assertEqual(report.log, "all good")
        self.assertEqual(report.errors, "")
        self.assertEqual(report.file_name, "results.csv")
        self.assertEqual(report.status, "success")
        self.assertEqual(report.test_data, {"submission_id": 1})

    def test_missing_required_field_raises_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.generator.create_report_from_testing_system({"metric": 0.5})

    def test_runtime_error_while_saving_returns_unsaved_report(self) -> None:
        payload = {
            "metric": 0.75,
            "log": "log info",
            "errors": "",
            "file_name": "results.csv",
        }

        with patch.object(Report, "save", autospec=True, side_effect=RuntimeError("no db")) as mock_save:
            report = self.generator.create_report_from_testing_system(payload)

        mock_save.assert_called_once()
        self.assertIsNone(report.pk)
        self.assertEqual(report.file_name, "results.csv")
        self.assertAlmostEqual(report.metric, 0.75)