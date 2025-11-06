from django.test import TestCase
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from unittest.mock import patch, mock_open, PropertyMock
from runner.services.prevalidation_service import run_prevalidation
from runner.models import Submission, PreValidation, ProblemDescriptor, Problem, ProblemData


class RunPrevalidationTestCase(TestCase):
    """Тесты для функции run_prevalidation"""

    maxDiff = None  # Чтобы Django не обрезал длинные diff'ы в assertEqual

    @patch("runner.services.prevalidation_service.transaction.atomic")
    @patch("runner.services.prevalidation_service.PreValidation.save")
    @patch("runner.services.prevalidation_service.Submission.save")
    @patch("builtins.open", new_callable=mock_open, read_data="id,value\n1,10\n2,20\n")
    def test_successful_prevalidation(self, mock_file, mock_sub_save, mock_preval_save, mock_atomic):
        """Успешная валидация корректного сабмишена"""
        # Создаём объекты задачи и её описателя
        problem = Problem.objects.create(title="Test Problem", created_at=timezone.now().date())
        descriptor = ProblemDescriptor.objects.create(
            problem=problem,
            id_column="id",
            target_column="value",
            target_type="int",
            check_order=False
        )

        # Пример файла sample submission
        problem_data = ProblemData.objects.create(problem=problem)
        problem_data.sample_submission_file.save('sample.csv', ContentFile("id,value\n1,10\n2,20\n"), save=True)

        # Мокаем property output_columns
        type(descriptor).output_columns = PropertyMock(return_value=["value"])

        # Create a test user
        test_user = User.objects.create_user(username='testuser')
        
        # Создаём реальный Submission с файлом
        submission = Submission.objects.create(problem=problem, user=test_user)
        submission.file.save('submission.csv', ContentFile("id,value\n1,10\n2,20\n"), save=True)

        # Подменяем чтение файла на корректные данные
        sample_data = "id,value\n1,10\n2,20\n"
        with patch("builtins.open", mock_open(read_data=sample_data)):
            preval = run_prevalidation(submission)

        # Проверяем результат
        self.assertEqual(preval.status, "passed")
        self.assertEqual(preval.errors_count, 0)
        self.assertEqual(preval.warnings_count, 0)
        self.assertEqual(preval.unique_ids, 2)
        self.assertEqual(preval.first_id, "1")
        self.assertEqual(preval.last_id, "2")

        # Проверяем, что save вызывался
        mock_sub_save.assert_called()

    @patch("runner.services.prevalidation_service.transaction.atomic")
    @patch("runner.services.prevalidation_service.PreValidation.objects.create")
    @patch("runner.services.prevalidation_service.Submission.save")
    @patch("builtins.open", side_effect=Exception("File not found"))
    def test_file_read_error(self, mock_file, mock_sub_save, mock_preval_save, mock_atomic):
        """Ошибка при чтении файла сабмишена"""
        problem = Problem.objects.create(title="Test Problem", created_at=timezone.now().date())
        descriptor = ProblemDescriptor.objects.create(
            problem=problem,
            id_column="id",
            target_column="value",
            target_type="int",
            check_order=False
        )

        problem_data = ProblemData.objects.create(problem=problem)
        problem_data.sample_submission_file.save('sample.csv', ContentFile("id,value\n1,10\n2,20\n"), save=True)

        type(descriptor).output_columns = PropertyMock(return_value=["value"])

        # Create a test user
        test_user = User.objects.create_user(username='testuser2')
        
        submission = Submission.objects.create(problem=problem, user=test_user)
        submission.file.save('submission.csv', ContentFile("invalid"), save=True)

        preval = run_prevalidation(submission)

        # Проверяем, что статус failed и ошибка чтения зафиксирована
        self.assertEqual(preval.status, "failed")
        self.assertTrue(any("Cannot read file" in err for err in preval.errors))
        mock_preval_save.assert_called()
        mock_sub_save.assert_called()

    @patch("runner.services.prevalidation_service.transaction.atomic")
    @patch("runner.services.prevalidation_service.PreValidation.objects.create")
    @patch("runner.services.prevalidation_service.Submission.save")
    def test_row_count_mismatch(self, mock_sub_save, mock_preval_save, mock_atomic):
        """Несовпадение количества строк между сабмишеном и sample submission"""
        problem = Problem.objects.create(title="Test Problem", created_at=timezone.now().date())
        descriptor = ProblemDescriptor.objects.create(
            problem=problem,
            id_column="id",
            target_column="value",
            target_type="int",
            check_order=False
        )

        problem_data = ProblemData.objects.create(problem=problem)
        problem_data.sample_submission_file.save('sample.csv', ContentFile("id,value\n1,10\n2,20\n"), save=True)

        type(descriptor).output_columns = PropertyMock(return_value=["value"])

        # Сабмишен содержит лишнюю строку
        submission_data = "id,value\n1,10\n2,20\n3,30\n"
        
        # Create a test user
        test_user = User.objects.create_user(username='testuser3')
        
        submission = Submission.objects.create(problem=problem, user=test_user)
        submission.file.save('submission.csv', ContentFile(submission_data), save=True)
        submission_data = "id,value\n1,10\n2,20\n3,30\n"
        sample_data = "id,value\n1,10\n2,20\n"

        # Последовательно открываем сначала submission, потом sample
        m_open = mock_open()
        m_open.side_effect = [
            mock_open(read_data=submission_data).return_value,
            mock_open(read_data=sample_data).return_value,
        ]

        with patch("builtins.open", m_open):
            preval = run_prevalidation(submission)

        # Проверяем, что валидация не прошла
        self.assertEqual(preval.status, "failed")
        self.assertGreater(preval.errors_count, 0)
        self.assertTrue(any("Row count does not match sample submission" in err for err in preval.errors))
        mock_preval_save.assert_called()
        mock_sub_save.assert_called()
