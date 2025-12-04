from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthorizationViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()

        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123'
        )

        self.valid_register_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123'
        }

        self.valid_login_data = {
            'username': 'testuser',
            'password': 'TestPass123'
        }

        self.register_url = reverse('runner:register')
        self.login_url = reverse('runner:login')
        self.logout_url = reverse('runner:logout')
        self.main_page_url = reverse('runner:main_page')

        self.api_register_url = reverse('runner:backend_register')
        self.api_login_url = reverse('runner:backend_login')
        self.api_logout_url = reverse('runner:backend_logout')
        self.api_current_user_url = reverse('runner:backend_current_user')
        self.api_check_auth_url = reverse('runner:backend_check_auth')
        self.api_csrf_url = reverse('runner:backend_csrf_token')
        self.api_token_url = reverse('runner:token_obtain_pair')
        self.api_token_refresh_url = reverse('runner:token_refresh')

    def test_register_view_get(self):
        response = self.client.get(self.register_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'runner/authorization/register.html')
        self.assertIn('form', response.context)

    def test_register_view_post_valid(self):
        response = self.client.post(self.register_url, self.valid_register_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('runner:login'))

        user_exists = User.objects.filter(username='newuser').exists()
        self.assertTrue(user_exists)

    def test_register_view_post_invalid(self):
        invalid_data = {
            'username': '',
            'email': 'invalid-email',
            'password1': 'short',
            'password2': 'different'
        }

        response = self.client.post(self.register_url, invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'runner/authorization/register.html')

        form = response.context['form']
        self.assertFalse(form.is_valid())

        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('password1', form.errors)

    def test_login_view_get(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'runner/authorization/login.html')
        self.assertIn('form', response.context)

    def test_login_view_post_valid(self):
        response = self.client.post(self.login_url, self.valid_login_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.main_page_url)

        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'testuser')

    def test_login_view_post_invalid(self):
        invalid_data = {
            'username': 'wronguser',
            'password': 'wrongpass'
        }

        response = self.client.post(self.login_url, invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'runner/authorization/login.html')

        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_logout_view_authenticated(self):
        self.client.login(username='testuser', password='TestPass123')
        response = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.main_page_url)

        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_view_anonymous(self):
        response = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.main_page_url)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_backend_register_api_valid(self):
        response = self.api_client.post(
            self.api_register_url,
            data=self.valid_register_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Регистрация успешна')

        self.assertEqual(response.data['user']['username'], 'newuser')
        self.assertEqual(response.data['user']['email'], 'newuser@example.com')

        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

        user_exists = User.objects.filter(username='newuser').exists()
        self.assertTrue(user_exists)

    def test_backend_register_api_invalid(self):
        invalid_data = {
            'username': '',
            'email': 'invalid',
            'password1': 'short',
            'password2': 'different'
        }

        response = self.api_client.post(
            self.api_register_url,
            data=invalid_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)

        errors = response.data['errors']
        self.assertIn('username', errors)
        self.assertIn('email', errors)
        self.assertIn('password1', errors)

    def test_backend_register_api_duplicate_username(self):
        duplicate_data = {
            'username': 'testuser',
            'email': 'another@example.com',
            'password1': 'AnotherPass123',
            'password2': 'AnotherPass123'
        }

        response = self.api_client.post(
            self.api_register_url,
            data=duplicate_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)
        self.assertIn('username', response.data['errors'])

    def test_backend_login_api_valid(self):
        response = self.api_client.post(
            self.api_login_url,
            data=self.valid_login_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Вход выполнен успешно')

        self.assertEqual(response.data['user']['username'], 'testuser')
        self.assertEqual(response.data['user']['email'], 'test@example.com')

        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

    def test_backend_login_api_invalid(self):
        invalid_data = {
            'username': 'wronguser',
            'password': 'wrongpass'
        }

        response = self.api_client.post(
            self.api_login_url,
            data=invalid_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)
        self.assertIn('__all__', response.data['errors'])

    def test_backend_login_api_empty_data(self):
        empty_data = {
            'username': '',
            'password': ''
        }

        response = self.api_client.post(
            self.api_login_url,
            data=empty_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)

    def test_backend_logout_api_authenticated(self):
        login_response = self.api_client.post(
            self.api_login_url,
            data=self.valid_login_data,
            format='json'
        )

        access_token = login_response.data['tokens']['access']

        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        response = self.api_client.post(self.api_logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Выход выполнен успешно')

    def test_backend_logout_api_unauthenticated(self):
        response = self.api_client.post(self.api_logout_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_backend_current_user_api_authenticated(self):
        login_response = self.api_client.post(
            self.api_login_url,
            data=self.valid_login_data,
            format='json'
        )
        access_token = login_response.data['tokens']['access']

        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        response = self.api_client.get(self.api_current_user_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertTrue(response.data['is_authenticated'])

    def test_backend_current_user_api_unauthenticated(self):
        response = self.api_client.get(self.api_current_user_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_backend_check_auth_api_authenticated(self):
        self.client.login(username='testuser', password='TestPass123')

        response = self.client.get(self.api_check_auth_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_authenticated'])
        self.assertEqual(response.data['user']['username'], 'testuser')
        self.assertEqual(response.data['user']['email'], 'test@example.com')

    def test_backend_check_auth_api_unauthenticated(self):
        response = self.api_client.get(self.api_check_auth_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_authenticated'])
        self.assertIsNone(response.data['user']['username'])
        self.assertIsNone(response.data['user']['email'])

    def test_get_csrf_token_api(self):
        response = self.api_client.get(self.api_csrf_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('csrfToken', response.data)
        self.assertIsInstance(response.data['csrfToken'], str)
        self.assertTrue(len(response.data['csrfToken']) > 0)

    def test_register_password_mismatch(self):
        data = {
            'username': 'user1',
            'email': 'user1@example.com',
            'password1': 'Password123',
            'password2': 'Different123'
        }

        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_register_weak_password_only(self):
        data = {
            'username': 'user2',
            'email': 'user2@example.com',
            'password1': '12345678',
            'password2': '87654321'
        }

        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_login_with_email_instead_of_username(self):
        data = {
            'username': 'test@example.com',
            'password': 'TestPass123'
        }

        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())

    def test_multiple_simultaneous_logins(self):
        users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'user{i}',
                password=f'pass{i}'
            )
            users.append(user)

        for i in range(3):
            response = self.client.post(self.login_url, {
                'username': f'user{i}',
                'password': f'pass{i}'
            })

            self.assertEqual(response.status_code, 302)

            self.client.logout()

    def test_session_persistence(self):
        self.client.login(username='testuser', password='TestPass123')

        response = self.client.get(self.main_page_url)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_csrf_protection(self):
        response = self.client.post(self.api_register_url, self.valid_register_data)

        self.assertNotEqual(response.status_code, 403)

    def test_jwt_token_obtain(self):
        response = self.api_client.post(
            self.api_token_url,
            data={'username': 'testuser', 'password': 'TestPass123'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_jwt_token_refresh(self):
        token_response = self.api_client.post(
            self.api_token_url,
            data={'username': 'testuser', 'password': 'TestPass123'},
            format='json'
        )

        refresh_token = token_response.data['refresh']

        refresh_response = self.api_client.post(
            self.api_token_refresh_url,
            data={'refresh': refresh_token},
            format='json'
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)


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
        self.assertFalse(user.is_staff)

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
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "error")
