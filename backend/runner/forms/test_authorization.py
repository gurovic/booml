from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
import tempfile
from unittest.mock import patch
from runner.models import TeacherAccessRequest
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

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_register_form_teacher_role_creates_pending_request_without_staff(self):
        proof = SimpleUploadedFile(
            "mesh-proof.png",
            b"proof",
            content_type="image/png",
        )
        data = {
            "username": "teacher_user",
            "email": "teacher@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            "role": "teacher",
            "teacher_comment": "Скриншот из МЭШ",
        }
        form = RegisterForm(data, {"teacher_proof": proof})
        self.assertTrue(form.is_valid(), msg=form.errors)
        user = form.save()
        self.assertFalse(user.is_staff)
        teacher_request = TeacherAccessRequest.objects.get(user=user)
        self.assertEqual(teacher_request.status, TeacherAccessRequest.STATUS_PENDING)
        self.assertEqual(teacher_request.comment, "Скриншот из МЭШ")
        teacher_request.proof.delete()

    def test_register_form_teacher_role_requires_proof(self):
        data = {
            "username": "teacher_no_proof",
            "email": "teacher_no_proof@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            "role": "teacher",
        }
        form = RegisterForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("teacher_proof", form.errors)

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

    @override_settings(
        CAPTCHA_PROVIDER="turnstile",
        CAPTCHA_DISABLE_DURING_TESTS=False,
        TURNSTILE_SITE_KEY="test-site-key",
        TURNSTILE_SECRET_KEY="test-secret-key",
    )
    def test_captcha_token_is_required_when_enabled(self):
        data = {
            "username": "captcha_missing_user",
            "email": "captcha_missing@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            "role": "student",
        }
        form = RegisterForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("captcha_token", form.errors)

    @override_settings(
        CAPTCHA_PROVIDER="turnstile",
        CAPTCHA_DISABLE_DURING_TESTS=False,
        TURNSTILE_SITE_KEY="test-site-key",
        TURNSTILE_SECRET_KEY="test-secret-key",
    )
    @patch("runner.forms.authorization.verify_turnstile_token")
    def test_captcha_token_allows_registration_when_valid(self, verify_turnstile_token_mock):
        verify_turnstile_token_mock.return_value = {"success": True}
        data = {
            "username": "captcha_user",
            "email": "captcha@example.com",
            "password1": "strongpass123",
            "password2": "strongpass123",
            "role": "student",
            "captcha_token": "valid-token",
        }
        form = RegisterForm(data)
        self.assertTrue(form.is_valid(), msg=form.errors)
