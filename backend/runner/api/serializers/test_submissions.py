from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory

from app.models.task import Task
from app.models.submision import Submission
from .submissions import SubmissionCreateSerializer

User = get_user_model()

class SubmissionSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username="u1", password="pass")
        self.task = Task.objects.create(
            title="Demo Task",
            statement="predict something",
            created_at=date.today(),
        )

    def test_create_ok(self):
        req = self.factory.post("/api/submissions/")
        req.user = self.user
        f = SimpleUploadedFile("preds.csv", b"id,pred\n1,0.1\n", content_type="text/csv")
        ser = SubmissionCreateSerializer(
            data={"task_id": self.task.id, "file": f},
            context={"request": req},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        sub = ser.save()
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.task, self.task)

    def test_reject_non_csv(self):
        req = self.factory.post("/api/submissions/")
        req.user = self.user
        f = SimpleUploadedFile("bad.txt", b"oops", content_type="text/plain")
        ser = SubmissionCreateSerializer(
            data={"task_id": self.task.id, "file": f},
            context={"request": req},
        )
        self.assertFalse(ser.is_valid())
        self.assertIn("file", ser.errors)
