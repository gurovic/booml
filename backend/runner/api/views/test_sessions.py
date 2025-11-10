from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from runner.models import Notebook
from runner.services.runtime import _sessions, create_session, get_session

User = get_user_model()


class NotebookSessionAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.client.login(username="owner", password="pass123")
        self.notebook = Notebook.objects.create(owner=self.user, title="My NB")
        self.create_url = reverse("notebook-session-create")
        self.reset_url = reverse("session-reset")
        _sessions.clear()

    def tearDown(self):
        _sessions.clear()

    def test_create_session_success(self):
        resp = self.client.post(self.create_url, {"notebook_id": self.notebook.id})
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        data = resp.json()
        session_id = data["session_id"]
        self.assertTrue(session_id.endswith(str(self.notebook.id)))
        self.assertEqual(data["status"], "created")
        self.assertIn(session_id, _sessions)

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
