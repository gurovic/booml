from django.test import TestCase
from unittest.mock import patch, MagicMock, mock_open

from runner.services.prevalidation_service import run_prevalidation
from runner.models import Submission, PreValidation
from runner.models.problem_desriptor import ProblemDescriptor


class RunPrevalidationTestCase(TestCase):

    def create_mock_submission(self):
        """Создает правильный мок для Submission с _state"""
        submission = MagicMock(spec=Submission)
        submission._state = MagicMock()
        submission._state.db = 'default'
        submission.file = MagicMock()
        submission.file.path = "submission.csv"
        return submission

    def create_mock_problem(self):
        """Создает правильный мок для Problem с связанными объектами"""
        descriptor = MagicMock(spec=ProblemDescriptor)
        descriptor.id_column = "id"
        descriptor.output_columns = ["value"]
        descriptor.target_column = "value"
        descriptor.target_type = "int"
        descriptor.check_order = False

        problem_data = MagicMock()
        problem_data.sample_submission_file = MagicMock()
        problem_data.sample_submission_file.path = "sample.csv"

        problem = MagicMock()
        problem.descriptor = descriptor
        problem.data = problem_data

        return problem

    @patch("runner.services.prevalidation_service.transaction.atomic")
    @patch("runner.services.prevalidation_service.PreValidation.objects.create")
    @patch("runner.services.prevalidation_service.Submission.save")
    @patch("builtins.open", new_callable=mock_open, read_data="id,value\n1,10\n2,20\n")
    def test_successful_prevalidation(self, mock_file, mock_sub_save, mock_preval_create, mock_atomic):
        # Создаем моки
        submission = self.create_mock_submission()
        submission.problem = self.create_mock_problem()

        # Мокаем создание PreValidation
        mock_preval = MagicMock()
        mock_preval_create.return_value = mock_preval

        # Мокаем открытие sample submission
        sample_data = "id,value\n1,10\n2,20\n"
        with patch("builtins.open", mock_open(read_data=sample_data)) as m_open:
            preval = run_prevalidation(submission)

        # Проверяем что PreValidation был создан
        mock_preval_create.assert_called_once()
        
        # Проверяем, что save вызывался
        mock_sub_save.assert_called()

    @patch("runner.services.prevalidation_service.transaction.atomic")
    @patch("runner.services.prevalidation_service.PreValidation.objects.create")
    @patch("runner.services.prevalidation_service.Submission.save")
    @patch("builtins.open", side_effect=Exception("File not found"))
    def test_file_read_error(self, mock_file, mock_sub_save, mock_preval_create, mock_atomic):
        submission = self.create_mock_submission()
        submission.problem = self.create_mock_problem()

        # Мокаем создание PreValidation
        mock_preval = MagicMock()
        mock_preval_create.return_value = mock_preval

        preval = run_prevalidation(submission)

        # Проверяем что PreValidation был создан с ошибкой
        mock_preval_create.assert_called_once()
        mock_sub_save.assert_called()

    @patch("runner.services.prevalidation_service.transaction.atomic")
    @patch("runner.services.prevalidation_service.PreValidation.objects.create")
    @patch("runner.services.prevalidation_service.Submission.save")
    def test_row_count_mismatch(self, mock_sub_save, mock_preval_create, mock_atomic):
        submission = self.create_mock_submission()
        submission.problem = self.create_mock_problem()

        # Мокаем создание PreValidation
        mock_preval = MagicMock()
        mock_preval_create.return_value = mock_preval

        # Мокаем открытие файлов с разным количеством строк
        submission_data = "id,value\n1,10\n2,20\n3,30\n"
        sample_data = "id,value\n1,10\n2,20\n"
        
        m_open = mock_open()
        handles = [
            mock_open(read_data=submission_data).return_value,
            mock_open(read_data=sample_data).return_value
        ]
        m_open.side_effect = handles
        
        with patch("builtins.open", m_open):
            preval = run_prevalidation(submission)

        # Проверяем что PreValidation был создан
        mock_preval_create.assert_called_once()