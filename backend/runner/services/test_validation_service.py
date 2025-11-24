from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch

from .validation_service import run_pre_validation


class RunPreValidationTests(SimpleTestCase):
    def test_delegates_to_prevalidation_service(self) -> None:
        submission = MagicMock()
        prevalidation_result = MagicMock()

        with patch(
            "runner.services.validation_service.prevalidation_service.run_prevalidation",
            return_value=prevalidation_result,
        ) as mock_run_prevalidation:
            result = run_pre_validation(
                submission,
                descriptor={"key": "value"},
                id_column=1,
                check_order=True,
                extra_argument=True,
            )

        mock_run_prevalidation.assert_called_once_with(submission)
        self.assertIs(result, prevalidation_result)