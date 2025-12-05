from django.test import TestCase
from django.contrib.auth import get_user_model
from runner.forms.authorization import RegisterForm

User = get_user_model()


class RegisterFormTests(TestCase):
    def test_register_form_student_role_creates_user_without_staff(self):
        data = {
            "username": "student_user",
            "email": "student@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            "role": "student",
        }
        form = RegisterForm(data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        user = form.save()
        self.assertEqual(user.username, "student_user")
        self.assertFalse(user.is_staff)

    def test_register_form_teacher_role_creates_staff_user(self):
        data = {
            "username": "teacher_user",
            "email": "teacher@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            "role": "teacher",
        }
        form = RegisterForm(data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        user = form.save()

    def test_role_field_is_required(self):
        data = {
            "username": "no_role_user",
            "email": "no_role@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            # role omitted
        }
        form = RegisterForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_invalid_role_rejected(self):
        data = {
            "username": "bad_role_user",
            "email": "bad_role@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            "role": "admin",  # invalid choice
        }
        form = RegisterForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_password_mismatch_rejected(self):
        data = {
            "username": "mismatch_user",
            "email": "mismatch@example.com",
            "password1": "strongpass123",
            "password2": "differentpass456",
            "role": "student",
        }
        form = RegisterForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_short_password_rejected(self):
        data = {
            "username": "short_pass_user",
            "email": "short@example.com",
            "password1": "short",
            "password2": "short",
            "role": "student",
        }
        form = RegisterForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)
