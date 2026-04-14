import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Notebook


class UpdateNotebookDeviceViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_user(username="device-user", password="pass")
        self.notebook = Notebook.objects.create(owner=self.user, title="Notebook")
        self.client.force_login(self.user)

    def test_backend_alias_updates_compute_device(self):
        profile = self.user.profile
        profile.gpu_access = True
        profile.save(update_fields=["gpu_access"])
        response = self.client.patch(
            reverse("runner:backend_update_notebook_device", args=[self.notebook.id]),
            data=json.dumps({"compute_device": "gpu"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["compute_device"], "gpu")

        self.notebook.refresh_from_db()
        self.assertEqual(self.notebook.compute_device, Notebook.ComputeDevice.GPU)

    def test_rejects_gpu_without_access(self):
        response = self.client.patch(
            reverse("runner:backend_update_notebook_device", args=[self.notebook.id]),
            data=json.dumps({"compute_device": "gpu"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "Нет прав на GPU")

        self.notebook.refresh_from_db()
        self.assertEqual(self.notebook.compute_device, Notebook.ComputeDevice.CPU)

    def test_rejects_invalid_compute_device(self):
        response = self.client.patch(
            reverse("runner:backend_update_notebook_device", args=[self.notebook.id]),
            data=json.dumps({"compute_device": "tpu"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.notebook.refresh_from_db()
        self.assertEqual(self.notebook.compute_device, Notebook.ComputeDevice.CPU)
