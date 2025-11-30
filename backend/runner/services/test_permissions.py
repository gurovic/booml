from django.test import TestCase
from django.contrib.auth import get_user_model
from django.http import Http404
from ..models import Notebook
from ..services.permissions import get_user_notebook_or_404  # путь к твоему сервису

User = get_user_model()


class NotebookPermissionServiceTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="pass1")
        self.user2 = User.objects.create_user(username="user2", password="pass2")
        self.notebook1 = Notebook.objects.create(title="User1 Notebook", owner=self.user1)

    def test_owner_can_get_notebook(self):
        notebook = get_user_notebook_or_404(self.user1, self.notebook1.id)
        self.assertEqual(notebook, self.notebook1)

    def test_other_user_cannot_get_notebook(self):
        with self.assertRaises(Http404):
            get_user_notebook_or_404(self.user2, self.notebook1.id)

    def test_anonymous_user_cannot_get_notebook(self):
        with self.assertRaises(Http404):
            get_user_notebook_or_404(None, self.notebook1.id)

    def test_nonexistent_notebook_raises_404(self):
        with self.assertRaises(Http404):
            get_user_notebook_or_404(self.user1, 9999)
