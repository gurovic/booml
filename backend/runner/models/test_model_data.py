from django.test import TestCase
from django.utils import timezone
from .problem import Problem
from .problem_data import ProblemData
from django.core.files.uploadedfile import SimpleUploadedFile


class ProblemDataModelTest(TestCase):
    def setUp(self):
        self.problem = Problem.objects.create(
            title="Test Problem",
            statement="Описание задачи",
            rating=1200,
            created_at=timezone.now().date()
        )

    def test_create_problem_data(self):
        train = SimpleUploadedFile("train.csv", b"col1,col2\n1,2")
        test = SimpleUploadedFile("test.csv", b"col1\n3")
        answer = SimpleUploadedFile("answer.csv", b"col1\n2")
        sample = SimpleUploadedFile("sample.csv", b"col1\n2")

        pdata = ProblemData.objects.create(
            problem=self.problem,
            train_file=train,
            test_file=test,
            answer_file=answer,
            sample_submission_file=sample,
        )

        self.assertEqual(pdata.problem, self.problem)
        self.assertTrue(pdata.train_file.name.endswith("train.csv"))
        self.assertTrue(pdata.test_file.name.endswith("test.csv"))
        self.assertTrue(pdata.answer_file.name.endswith("answer.csv"))
        self.assertTrue(pdata.sample_submission_file.name.endswith("sample.csv"))

        self.assertIsNotNone(pdata.created_at)
        self.assertIsNotNone(pdata.updated_at)

        self.assertEqual(str(pdata), f"ProblemData for {self.problem}")

    def test_one_to_one_relationship(self):
        ProblemData.objects.create(problem=self.problem)
        with self.assertRaises(Exception):
            ProblemData.objects.create(problem=self.problem)