from typing import Optional

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from runner.forms import SubmissionUploadForm


class SubmissionUploadFormTests(SimpleTestCase):
    def _make_file(self, name: str = "submission.csv", content: Optional[bytes] = None):
        if content is None:
            content = b"id,target\n1,0.1\n"
        return SimpleUploadedFile(name, content, content_type="text/csv")

    def test_valid_csv_passes_validation(self):
        form = SubmissionUploadForm(data={}, files={"file": self._make_file()})
        self.assertTrue(form.is_valid())

    def test_non_csv_extension_is_rejected(self):
        form = SubmissionUploadForm(data={}, files={"file": self._make_file(name="answer.txt")})
        self.assertFalse(form.is_valid())
        self.assertIn("CSV", form.errors["file"][0])

    def test_max_file_size_validation(self):
        big_content = b"x" * 2
        form = SubmissionUploadForm(
            data={},
            files={"file": self._make_file(content=big_content)},
            max_file_mb=0.000001,  # ~= 1 byte
        )
        self.assertFalse(form.is_valid())
        self.assertIn("слишком большой", form.errors["file"][0])
