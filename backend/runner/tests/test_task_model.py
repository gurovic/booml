from django.test import TestCase
from ..models.task import Task
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

class TaskModelTest(TestCase):
    def test_create_task(self):
        task = Task.objects.create(
            title="MNIST Classifier",
            statement="**Hello** _world_",
            rating=1200,
            data_file=SimpleUploadedFile("data.csv", b"col1,col2\n1,2"),
        )
        self.assertEqual(task.title, "MNIST Classifier")
        self.assertIn("Hello", task.statement)

    def test_rating_validation(self):
        task = Task(title="Test", statement="...", rating=100)
        with self.assertRaises(ValidationError):
            task.full_clean()