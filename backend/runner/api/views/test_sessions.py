from http import HTTPStatus
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from runner.models import Notebook
from runner.services import vm_agent, vm_manager
from runner.services.runtime import _sessions, create_session, get_session, run_code

User = get_user_model()


class NotebookSessionAPITests(TestCase):
    def setUp(self):
        self.sandbox_tmp = TemporaryDirectory()
        self.vm_tmp = TemporaryDirectory()
        self.override = override_settings(
            RUNTIME_SANDBOX_ROOT=self.sandbox_tmp.name,
            RUNTIME_VM_ROOT=self.vm_tmp.name,
            RUNTIME_VM_BACKEND="local",
        )
        self.override.enable()
        vm_manager.reset_vm_manager()
        vm_agent.reset_vm_agents()
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.client.login(username="owner", password="pass123")
        self.notebook = Notebook.objects.create(owner=self.user, title="My NB")
        self.create_url = reverse("notebook-session-create")
        self.reset_url = reverse("session-reset")
        self.stop_url = reverse("session-stop")
        self.files_url = reverse("session-files")
        self.download_url = reverse("session-file-download")
        _sessions.clear()

    def tearDown(self):
        vm_manager.reset_vm_manager()
        vm_agent.reset_vm_agents()
        _sessions.clear()
        self.override.disable()
        self.sandbox_tmp.cleanup()
        self.vm_tmp.cleanup()

    def test_create_session_success(self):
        resp = self.client.post(self.create_url, {"notebook_id": self.notebook.id})
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        data = resp.json()
        session_id = data["session_id"]
        self.assertTrue(session_id.endswith(str(self.notebook.id)))
        self.assertEqual(data["status"], "created")
        self.assertIn(session_id, _sessions)
        self.assertIn("vm", data)
        self.assertEqual(data["vm"]["id"], f"runner-{session_id.replace(':', '_')}")

    def test_create_session_forbidden_for_other_user(self):
        another = User.objects.create_user(username="other", password="pass456")
        other_nb = Notebook.objects.create(owner=another, title="Other NB")

        resp = self.client.post(self.create_url, {"notebook_id": other_nb.id})
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)
        self.assertNotIn(f"notebook:{other_nb.id}", _sessions)

    def test_reset_session_success(self):
        session_id = f"notebook:{self.notebook.id}"
        first_session = create_session(session_id)

        resp = self.client.post(self.reset_url, {"session_id": session_id})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(data["status"], "reset")
        self.assertIn("vm", data)

        second_session = get_session(session_id, touch=False)
        self.assertIsNotNone(second_session)
        self.assertIsNot(first_session, second_session)

    def test_reset_session_forbidden_for_other_user(self):
        another = User.objects.create_user(username="other2", password="pass789")
        other_nb = Notebook.objects.create(owner=another, title="Other NB")
        session_id = f"notebook:{other_nb.id}"
        create_session(session_id)

        resp = self.client.post(self.reset_url, {"session_id": session_id})

        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)
        # ensure session not reset: still same object
        original = get_session(session_id, touch=False)
        again = get_session(session_id, touch=False)
        self.assertIs(original, again)

    def test_reset_session_missing_returns_404(self):
        session_id = f"notebook:{self.notebook.id}"
        resp = self.client.post(self.reset_url, {"session_id": session_id})
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_files_listing(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        run_code(session_id, "open('result.txt','w').write('hello')")

        resp = self.client.get(f"{self.files_url}?session_id={session_id}")
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertTrue(any(item["path"] == "result.txt" for item in data.get("files", [])))
        self.assertIn("vm", data)

    def test_session_file_download(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        run_code(session_id, "open('download.txt','w').write('ping')")

        resp = self.client.get(f"{self.download_url}?session_id={session_id}&path=download.txt")
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        content = b"".join(resp.streaming_content)
        self.assertEqual(content, b"ping")

    def test_session_file_download_prevents_escape(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)

        resp = self.client.get(f"{self.download_url}?session_id={session_id}&path=../secret.txt")
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_stop_session_success(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)

        resp = self.client.post(self.stop_url, {"session_id": session_id})

        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(resp.json()["status"], "stopped")
        self.assertIsNone(get_session(session_id, touch=False))

    def test_stop_session_not_found(self):
        session_id = f"notebook:{self.notebook.id}"
        resp = self.client.post(self.stop_url, {"session_id": session_id})
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_files_missing_session_returns_404(self):
        session_id = f"notebook:{self.notebook.id}"
        resp = self.client.get(f"{self.files_url}?session_id={session_id}")
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
