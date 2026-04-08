import csv
import io
import tempfile
import zipfile
from pathlib import Path

from django.core.files.storage import FileSystemStorage
from django.core.management import CommandError, call_command
from django.test import TestCase

from runner.management.commands.restore_problem_data_from_zip import RESTORE_SPECS
from runner.models import Problem, ProblemData, ProblemDescriptor
from runner.services.custom_metric import MetricCodeExecutor


class RestoreProblemDataFromZipCommandTests(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.media_root = self.root / "media"
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.zip_path = self.root / "problem_data.zip"
        self._original_storages = {}
        for field_name in (
            "train_file",
            "test_file",
            "sample_submission_file",
            "answer_file",
        ):
            field = ProblemData._meta.get_field(field_name)
            self._original_storages[field_name] = field.storage
            field.storage = FileSystemStorage(location=str(self.media_root), base_url="/media/")

    def tearDown(self):
        for field_name, storage in self._original_storages.items():
            ProblemData._meta.get_field(field_name).storage = storage
        self.tmpdir.cleanup()

    def _create_problem(self, problem_id: int) -> Problem:
        spec = RESTORE_SPECS[problem_id]
        return Problem.objects.create(
            id=problem_id,
            title=spec.expected_title,
            statement="demo",
            rating=800,
            is_published=True,
        )

    def _write_zip(self, entries: dict[str, str]) -> None:
        with zipfile.ZipFile(self.zip_path, "w") as archive:
            archive.writestr("__MACOSX/problem_data/ignored.txt", "junk")
            archive.writestr("problem_data/placeholder/", "")
            for member, payload in entries.items():
                archive.writestr(member, payload)

    def _call_command(self, *args):
        stdout = io.StringIO()
        call_command("restore_problem_data_from_zip", *args, stdout=stdout)
        return stdout.getvalue()

    def _read_header(self, file_path: Path) -> list[str]:
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            return next(csv.reader(handle))

    def test_missing_selected_problem_raises_command_error(self):
        self._create_problem(4)
        self._write_zip({})

        with self.assertRaises(CommandError):
            self._call_command(
                "--zip",
                str(self.zip_path),
                "--problem-id",
                "4",
                "--problem-id",
                "10",
            )

    def test_dry_run_does_not_mutate_database(self):
        self._create_problem(4)
        legacy_descriptor = ProblemDescriptor.objects.create(
            problem_id=4,
            id_column="person",
            target_column="label",
            id_type="int",
            target_type="int",
            metric_name="rmse",
            metric="",
        )
        self._write_zip(
            {
                RESTORE_SPECS[4].files["train"]: "person,event_type\nperson_1,entry\n",
                RESTORE_SPECS[4].files["test"]: "person,event_type\nperson_1,entry\n",
                RESTORE_SPECS[4].files["sample_submission"]: "person,label\nperson_1,1\n",
                RESTORE_SPECS[4].files["answer"]: "person,label\nperson_1,1\n",
            }
        )

        output = self._call_command(
            "--zip",
            str(self.zip_path),
            "--problem-id",
            "4",
        )

        self.assertIn("apply=False", output)
        self.assertEqual(ProblemData.objects.count(), 0)
        legacy_descriptor.refresh_from_db()
        self.assertEqual(legacy_descriptor.metric_name, "rmse")
        self.assertFalse((self.media_root / "problem_data").exists())

    def test_apply_restores_files_and_descriptors(self):
        self._create_problem(4)
        self._create_problem(10)
        self._create_problem(13)
        ProblemDescriptor.objects.create(
            problem_id=4,
            id_column="person",
            target_column="label",
            id_type="int",
            target_type="int",
            metric_name="rmse",
            metric="",
        )
        self._write_zip(
            {
                RESTORE_SPECS[4].files["train"]: "person,event_type,event_time\nperson_1,entry,1\n",
                RESTORE_SPECS[4].files["test"]: "person,event_type,event_time\nperson_1,entry,1\n",
                RESTORE_SPECS[4].files["sample_submission"]: (
                    "person,label\n"
                    "person_1,1\nperson_2,0\nperson_3,1\nperson_4,0\nperson_5,1\nperson_6,0\n"
                ),
                RESTORE_SPECS[4].files["answer"]: (
                    "person,label\n"
                    "person_1,1\nperson_2,0\nperson_3,1\nperson_4,0\nperson_5,1\nperson_6,0\n"
                ),
                RESTORE_SPECS[10].files["train"]: "id,signal,alien_communication_prob\n1,10,0.5\n",
                RESTORE_SPECS[10].files["test"]: "id,signal\n1,10\n2,12\n",
                RESTORE_SPECS[10].files["sample_submission"]: ",alien_communication_prob\n1,0.2\n2,0.8\n",
                RESTORE_SPECS[10].files["answer"]: ",alien_communication_prob\n1,0.1\n2,0.7\n",
                RESTORE_SPECS[13].files["train"]: "id,cap_shape,id,is_poisonous\n1,bell,1,0\n2,flat,2,1\n",
                RESTORE_SPECS[13].files["test"]: "id,id,cap_shape,id\n1,1,bell,1\n2,2,flat,2\n",
                RESTORE_SPECS[13].files["sample_submission"]: "id,id,is_poisonous\n1,1,0\n2,2,1\n",
                RESTORE_SPECS[13].files["answer"]: "id,id,is_poisonous\n1,1,0\n2,2,1\n",
            }
        )

        output = self._call_command(
            "--zip",
            str(self.zip_path),
            "--apply",
            "--problem-id",
            "4",
            "--problem-id",
            "10",
            "--problem-id",
            "13",
        )

        self.assertIn("applied", output)
        self.assertEqual(ProblemData.objects.count(), 3)

        problem4_data = ProblemData.objects.get(problem_id=4)
        self.assertEqual(problem4_data.train_file.name, "problem_data/4/train/train.csv")
        self.assertEqual(problem4_data.test_file.name, "problem_data/4/test/test.csv")
        self.assertEqual(
            problem4_data.sample_submission_file.name,
            "problem_data/4/sample_submission/sample_submission.csv",
        )
        self.assertEqual(problem4_data.answer_file.name, "problem_data/4/answer/answer.csv")

        problem10_data = ProblemData.objects.get(problem_id=10)
        self.assertEqual(
            self._read_header(Path(problem10_data.sample_submission_file.path)),
            ["id", "alien_communication_prob"],
        )
        self.assertEqual(
            self._read_header(Path(problem10_data.answer_file.path)),
            ["id", "alien_communication_prob"],
        )

        problem13_data = ProblemData.objects.get(problem_id=13)
        self.assertEqual(
            self._read_header(Path(problem13_data.train_file.path)),
            ["id", "cap_shape", "is_poisonous"],
        )
        self.assertEqual(
            self._read_header(Path(problem13_data.test_file.path)),
            ["id", "cap_shape"],
        )
        self.assertEqual(
            self._read_header(Path(problem13_data.sample_submission_file.path)),
            ["id", "is_poisonous"],
        )
        self.assertEqual(
            self._read_header(Path(problem13_data.answer_file.path)),
            ["id", "is_poisonous"],
        )

        descriptor4 = ProblemDescriptor.objects.get(problem_id=4)
        self.assertEqual(descriptor4.id_column, "person")
        self.assertEqual(descriptor4.target_column, "label")
        self.assertEqual(descriptor4.id_type, "str")
        self.assertEqual(descriptor4.target_type, "int")
        self.assertEqual(descriptor4.metric_name, "jaccard_at_k")
        self.assertEqual(descriptor4.metric, "jaccard_at_k")
        self.assertEqual(descriptor4.score_direction, "maximize")
        self.assertEqual(descriptor4.score_ideal_metric, 1.0)

        metric_result = MetricCodeExecutor(descriptor4.metric_code).run(
            [1, 0, 1, 0, 1, 0],
            [1, 1, 1, 0, 1, 1],
        )
        self.assertAlmostEqual(metric_result["jaccard_at_k"], 0.6)

        descriptor10 = ProblemDescriptor.objects.get(problem_id=10)
        self.assertEqual(descriptor10.id_column, "id")
        self.assertEqual(descriptor10.target_column, "alien_communication_prob")
        self.assertEqual(descriptor10.metric_name, "rmse")
        self.assertEqual(descriptor10.metric, "rmse")

        descriptor13 = ProblemDescriptor.objects.get(problem_id=13)
        self.assertEqual(descriptor13.id_column, "id")
        self.assertEqual(descriptor13.target_column, "is_poisonous")
        self.assertEqual(descriptor13.metric_name, "accuracy")
