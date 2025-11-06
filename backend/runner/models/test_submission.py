import os
import shutil
import tempfile
from datetime import date

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from runner.models import Problem, Submission

User = get_user_model()


class SubmissionModelTests(TestCase):
    def setUp(self):
        # создаём отдельную временную директорию под MEDIA_ROOT
        self.media_dir = tempfile.mkdtemp(prefix="test_media_")
        self._override = override_settings(MEDIA_ROOT=self.media_dir)
        self._override.enable()

        self.user = User.objects.create_user(username="u1", password="pass")
        self.problem = Problem.objects.create(
            title="Demo Problem",
            statement="predict something",
            created_at=date.today(),
        )

    def tearDown(self):
        # откатываем MEDIA_ROOT и чистим временную директорию
        self._override.disable()
        if os.path.isdir(self.media_dir):
            shutil.rmtree(self.media_dir, ignore_errors=True)

    def test_code_size_file_path_and_str(self):
        content = b"id,pred\n1,0.1\n"
        f = SimpleUploadedFile("preds.csv", content, content_type="text/csv")

        sub = Submission.objects.create(user=self.user, problem=self.problem, file=f)

        self.assertGreater(sub.code_size, 0)
        # Используем sub.file.name вместо sub.file_path
        self.assertTrue(sub.file.name.endswith("preds.csv"))
        s = str(sub)
        self.assertIn(self.user.username, s)
        self.assertIn(str(self.problem), s)