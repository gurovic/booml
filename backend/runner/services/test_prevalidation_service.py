from unittest import TestCase
from unittest.mock import patch, MagicMock, mock_open
from runner.services.prevalidation_service import run_prevalidation
from runner.models import Submission, PreValidation, ProblemDescriptor

class RunPrevalidationTestCase(TestCase):

    @patch("runner.services.prevalidation_service.transaction.atomic")
    @patch("runner.services.prevalidation_service.PreValidation.save")
    @patch("runner.services.prevalidation_service.Submission.save")
    @patch("builtins.open", new_callable=mock_open, read_data="id,value\n1,10\n2,20\n")
    def test_successful_prevalidation(self, mock_file, mock_sub_save, mock_preval_save, mock_atomic):
        # Мокаем сабмишн и descriptor
        descriptor = MagicMock(spec=ProblemDescriptor)
        descriptor.id_column = "id"
        descriptor.output_columns = ["value"]
        descriptor.target_column = "value"
        descriptor.target_type = "int"
        descriptor.check_order = False

        problem = MagicMock()
        problem.descriptor = descriptor
        problem.data.sample_submission_file = "sample.csv"

        submission = MagicMock(spec=Submission)
        submission.file_path = "submission.csv"
        submission.problem = problem

        # Мокаем открытие sample submission
        sample_data = "id,value\n1,10\n2,20\n"
        with patch("builtins.open", mock_open(read_data=sample_data)) as m_open:
            preval = run_prevalidation(submission)

        # Проверяем поля prevalidation
        self.assertEqual(preval.status, "passed")
        self.assertEqual(preval.errors_count, 0)
        self.assertEqual(preval.warnings_count, 0)
        self.assertEqual(preval.unique_ids, 2)
        self.assertEqual(preval.first_id, "1")
        self.assertEqual(preval.last_id, "2")

        # Проверяем, что save вызывался
        mock_preval_save.assert_called()
        mock_sub_save.assert_called()

    @patch("runner.services.prevalidation_service.transaction.atomic")
    @patch("runner.services.prevalidation_service.PreValidation.save")
    @patch("runner.services.prevalidation_service.Submission.save")
    @patch("builtins.open", side_effect=Exception("File not found"))
    def test_file_read_error(self, mock_file, mock_sub_save, mock_preval_save, mock_atomic):
        descriptor = MagicMock(spec=ProblemDescriptor)
        descriptor.id_column = "id"
        descriptor.output_columns = ["value"]
        descriptor.target_column = "value"
        descriptor.target_type = "int"
        descriptor.check_order = False

        problem = MagicMock()
        problem.descriptor = descriptor
        problem.data.sample_submission_file = "sample.csv"

        submission = MagicMock(spec=Submission)
        submission.file_path = "submission.csv"
        submission.problem = problem

        preval = run_prevalidation(submission)

        self.assertEqual(preval.status, "failed")
        self.assertIn("Cannot read file", preval.errors[0])
        mock_preval_save.assert_called()
        mock_sub_save.assert_called()

    @patch("runner.services.prevalidation_service.transaction.atomic")
    @patch("runner.services.prevalidation_service.PreValidation.save")
    @patch("runner.services.prevalidation_service.Submission.save")
    def test_row_count_mismatch(self, mock_sub_save, mock_preval_save, mock_atomic):
        # Мокаем сабмишн и descriptor
        descriptor = MagicMock(spec=ProblemDescriptor)
        descriptor.id_column = "id"
        descriptor.output_columns = ["value"]
        descriptor.target_column = "value"
        descriptor.target_type = "int"
        descriptor.check_order = False

        problem = MagicMock()
        problem.descriptor = descriptor
        problem.data.sample_submission_file = "sample.csv"

        submission = MagicMock(spec=Submission)
        submission.file_path = "submission.csv"
        submission.problem = problem

        # Мокаем открытие файлов
        submission_data = "id,value\n1,10\n2,20\n3,30\n"
        sample_data = "id,value\n1,10\n2,20\n"
        with patch("builtins.open", mock_open(read_data=submission_data)) as m_sub, \
             patch("builtins.open", mock_open(read_data=sample_data)) as m_sample:
            # Здесь нужно различить открытие sample vs submission → используем side_effect
            m_open = mock_open()
            m_open.side_effect = [
                mock_open(read_data=submission_data).return_value,
                mock_open(read_data=sample_data).return_value
            ]
            with patch("builtins.open", m_open):
                preval = run_prevalidation(submission)

        self.assertIn("Row count does not match sample submission", preval.errors)
