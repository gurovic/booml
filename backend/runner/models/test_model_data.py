import os
from django.test import TestCase, override_settings
from tempfile import TemporaryDirectory
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from runner.models import Problem
from runner.models.problem_data import ProblemData


class ProblemDataModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._tmpdir = TemporaryDirectory()
        cls.override = override_settings(MEDIA_ROOT=cls._tmpdir.name)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        cls._tmpdir.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.problem = Problem.objects.create(
            title="Test Problem",
            statement="Описание задачи",
            rating=1200,
            created_at=timezone.now().date()
        )

    def test_create_problem_data(self):
        pdata = ProblemData.objects.create(
            problem=self.problem,
            train_file=SimpleUploadedFile("train.csv", b"col1,col2\n1,2"),
            test_file=SimpleUploadedFile("test.csv", b"col1\n3"),
            sample_submission_file=SimpleUploadedFile("sample.csv", b"col1\n2"),
        )

        self.assertEqual(pdata.problem, self.problem)
        self.assertIsNotNone(pdata.created_at)
        self.assertIsNotNone(pdata.updated_at)
        self.assertEqual(str(pdata), f"ProblemData for {self.problem}")

        def assert_file_ok(f, kind, prefix):
            if f:  # Проверяем только если файл существует
                self.assertIn(f"problem_data/{self.problem.id}/{kind}/", f.name)
                self.assertTrue(f.name.lower().endswith(".csv"))
                base = os.path.basename(f.name)
                self.assertTrue(base.startswith(prefix))

        assert_file_ok(pdata.train_file, "train", "train")
        assert_file_ok(pdata.test_file, "test", "test")
        assert_file_ok(pdata.sample_submission_file, "sample_submission", "sample")

    def test_one_to_one_relationship(self):
        ProblemData.objects.create(problem=self.problem)
        with self.assertRaises(IntegrityError):
            ProblemData.objects.create(problem=self.problem)