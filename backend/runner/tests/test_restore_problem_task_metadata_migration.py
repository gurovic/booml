import importlib

from django.apps import apps as global_apps
from django.test import TestCase

from runner.models import Problem, ProblemData, ProblemDescriptor


migration_module = importlib.import_module("runner.migrations.0028_restore_problem_task_metadata")


class RestoreProblemTaskMetadataMigrationTests(TestCase):
    def test_migration_upserts_repaired_problem_metadata(self):
        Problem.objects.create(
            id=4,
            title="AH Insiders!",
            statement="demo",
            rating=800,
            is_published=True,
        )
        Problem.objects.create(
            id=10,
            title="Alien contacts",
            statement="demo",
            rating=800,
            is_published=True,
        )

        ProblemDescriptor.objects.create(
            problem_id=4,
            id_column="person",
            target_column="label",
            id_type="int",
            target_type="int",
            metric_name="rmse",
            metric="",
        )

        migration_module.apply_problem_task_repairs(global_apps, None)

        problem4_data = ProblemData.objects.get(problem_id=4)
        self.assertEqual(problem4_data.train_file.name, "problem_data/4/train/train.csv")
        self.assertEqual(problem4_data.test_file.name, "problem_data/4/test/test.csv")
        self.assertEqual(
            problem4_data.sample_submission_file.name,
            "problem_data/4/sample_submission/sample_submission.csv",
        )
        self.assertEqual(problem4_data.answer_file.name, "problem_data/4/answer/answer.csv")

        problem10_data = ProblemData.objects.get(problem_id=10)
        self.assertEqual(problem10_data.train_file.name, "problem_data/10/train/train.csv")
        self.assertEqual(problem10_data.test_file.name, "problem_data/10/test/test.csv")
        self.assertEqual(
            problem10_data.sample_submission_file.name,
            "problem_data/10/sample_submission/sample_submission.csv",
        )
        self.assertEqual(problem10_data.answer_file.name, "problem_data/10/answer/answer.csv")

        descriptor4 = ProblemDescriptor.objects.get(problem_id=4)
        self.assertEqual(descriptor4.id_column, "person")
        self.assertEqual(descriptor4.target_column, "label")
        self.assertEqual(descriptor4.id_type, "str")
        self.assertEqual(descriptor4.target_type, "int")
        self.assertEqual(descriptor4.metric_name, "jaccard_at_k")
        self.assertEqual(descriptor4.metric, "jaccard_at_k")
        self.assertEqual(descriptor4.score_direction, "maximize")
        self.assertEqual(descriptor4.score_ideal_metric, 1.0)

        descriptor10 = ProblemDescriptor.objects.get(problem_id=10)
        self.assertEqual(descriptor10.id_column, "id")
        self.assertEqual(descriptor10.target_column, "alien_communication_prob")
        self.assertEqual(descriptor10.id_type, "int")
        self.assertEqual(descriptor10.target_type, "float")
        self.assertEqual(descriptor10.metric_name, "rmse")
        self.assertEqual(descriptor10.metric, "rmse")
