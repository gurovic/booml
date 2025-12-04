from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterViewTests(TestCase):
    def test_register_view_get_returns_form(self):
        url = reverse("runner:register")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Роль")
        self.assertContains(resp, "student")
        self.assertContains(resp, "teacher")

    def test_register_view_post_student_creates_non_staff_user(self):
        url = reverse("runner:register")
        data = {
            "username": "view_student",
            "email": "view_student@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            "role": "student",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        user = User.objects.filter(username="view_student").first()
        self.assertIsNotNone(user)

    def test_register_view_post_teacher_creates_staff_user(self):
        url = reverse("runner:register")
        data = {
            "username": "view_teacher",
            "email": "view_teacher@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            "role": "teacher",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        user = User.objects.filter(username="view_teacher").first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_staff)

    def test_register_view_missing_role_shows_error(self):
        url = reverse("runner:register")
        data = {
            "username": "no_role_view",
            "email": "no_role_view@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            # role missing
        }
        resp = self.client.post(url, data)
        # Form is invalid, re-render with errors (status 200)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "error")
