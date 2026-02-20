from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory
from unittest.mock import patch, MagicMock
import tempfile

from ...models import Profile
from ..serializers import (
    UserSerializer,
    ProfileSerializer,
    ProfileDetailSerializer,
    SubmissionReadSerializer,
    SubmissionDetailSerializer
)
from ...models import Problem, Submission

User = get_user_model()


class UserSerializerTests(TestCase):
    """Тесты для UserSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            first_name='Иван',
            last_name='Петров'
        )
        self.factory = APIRequestFactory()

    def test_user_serializer_fields(self):
        """Тест полей сериализатора пользователя"""
        serializer = UserSerializer(instance=self.user)
        data = serializer.data

        self.assertEqual(set(data.keys()), {'id', 'username', 'email', 'first_name',
                                            'last_name', 'full_name', 'role'})
        self.assertEqual(data['id'], self.user.id)
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['first_name'], 'Иван')
        self.assertEqual(data['last_name'], 'Петров')

    def test_get_full_name_with_first_and_last(self):
        """Тест получения полного имени когда есть имя и фамилия"""
        serializer = UserSerializer()
        full_name = serializer.get_full_name(self.user)
        self.assertEqual(full_name, 'Петров Иван')

    def test_get_full_name_with_only_first_name(self):
        """Тест получения полного имени когда есть только имя"""
        self.user.first_name = 'Иван'
        self.user.last_name = ''
        self.user.save()

        serializer = UserSerializer()
        full_name = serializer.get_full_name(self.user)
        self.assertEqual(full_name, 'Иван')

    def test_get_full_name_with_only_last_name(self):
        """Тест получения полного имени когда есть только фамилия"""
        self.user.first_name = ''
        self.user.last_name = 'Петров'
        self.user.save()

        serializer = UserSerializer()
        full_name = serializer.get_full_name(self.user)
        self.assertEqual(full_name, 'Петров')

    def test_get_full_name_without_name(self):
        """Тест получения полного имени когда нет имени и фамилии"""
        self.user.first_name = ''
        self.user.last_name = ''
        self.user.save()

        serializer = UserSerializer()
        full_name = serializer.get_full_name(self.user)
        self.assertEqual(full_name, 'testuser')

    def test_get_role_for_student(self):
        """Тест получения роли для обычного пользователя"""
        self.user.is_staff = False
        self.user.save()

        serializer = UserSerializer()
        role = serializer.get_role(self.user)
        self.assertEqual(role, 'student')

    def test_get_role_for_teacher(self):
        """Тест получения роли для учителя (staff)"""
        self.user.is_staff = True
        self.user.save()

        serializer = UserSerializer()
        role = serializer.get_role(self.user)
        self.assertEqual(role, 'teacher')


class ProfileSerializerTests(TestCase):
    """Тесты для ProfileSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            first_name='Иван',
            last_name='Петров'
        )
        self.profile = Profile.objects.get(user=self.user)
        self.factory = APIRequestFactory()

    def test_profile_serializer_fields(self):
        """Тест полей сериализатора профиля"""
        serializer = ProfileSerializer(instance=self.profile)
        data = serializer.data

        expected_fields = {'user', 'username', 'email', 'first_name', 'last_name',
                           'full_name', 'role', 'avatar', 'avatar_url'}
        self.assertEqual(set(data.keys()), expected_fields)

        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['first_name'], 'Иван')
        self.assertEqual(data['last_name'], 'Петров')
        self.assertEqual(data['full_name'], 'Петров Иван')
        self.assertEqual(data['role'], 'student')
        self.assertIsNone(data['avatar_url'])

    def test_profile_serializer_nested_user(self):
        """Тест вложенного пользователя в сериализаторе профиля"""
        serializer = ProfileSerializer(instance=self.profile)
        user_data = serializer.data['user']

        self.assertEqual(user_data['id'], self.user.id)
        self.assertEqual(user_data['username'], 'testuser')
        self.assertEqual(user_data['first_name'], 'Иван')
        self.assertEqual(user_data['last_name'], 'Петров')

    def test_get_full_name_method(self):
        """Тест метода get_full_name в ProfileSerializer"""
        serializer = ProfileSerializer()
        full_name = serializer.get_full_name(self.profile)
        self.assertEqual(full_name, 'Петров Иван')

    def test_get_role_method(self):
        """Тест метода get_role в ProfileSerializer"""
        serializer = ProfileSerializer()

        # Обычный пользователь
        role = serializer.get_role(self.profile)
        self.assertEqual(role, 'student')

        # Staff пользователь
        self.user.is_staff = True
        self.user.save()
        self.profile.refresh_from_db()

        role = serializer.get_role(self.profile)
        self.assertEqual(role, 'teacher')

    def test_get_avatar_url_without_avatar(self):
        """Тест получения URL аватара когда его нет"""
        serializer = ProfileSerializer()
        avatar_url = serializer.get_avatar_url(self.profile)
        self.assertIsNone(avatar_url)

    def test_get_avatar_url_with_avatar(self):
        """Тест получения URL аватара когда он есть"""
        # Создаем временное изображение
        with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp_file:
            tmp_file.write(b'test image content')
            tmp_file.seek(0)
            self.profile.avatar.save('test.jpg', tmp_file)

        serializer = ProfileSerializer(context={'request': None})
        avatar_url = serializer.get_avatar_url(self.profile)

        self.assertIsNotNone(avatar_url)
        self.assertTrue('/media/avatars/test' in avatar_url or 'test.jpg' in avatar_url)

        # Очищаем
        self.profile.avatar.delete()


class ProfileDetailSerializerTests(TestCase):
    """Тесты для ProfileDetailSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            first_name='Иван',
            last_name='Петров'
        )
        self.profile = Profile.objects.get(user=self.user)

        # Создаем задачу
        self.problem = Problem.objects.create(
            title='Тестовая задача'
        )

        # Создаем несколько тестовых посылок
        for i in range(5):
            Submission.objects.create(
                user=self.user,
                problem=self.problem,
                status='pending',
                metrics={'accuracy': 0.95 - i * 0.1}
            )

        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')

    def test_profile_detail_serializer_fields(self):
        """Тест полей детального сериализатора профиля"""
        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )
        data = serializer.data

        expected_fields = {'user', 'username', 'email', 'first_name', 'last_name',
                           'full_name', 'role', 'avatar', 'avatar_url', 'recent_submissions'}
        self.assertEqual(set(data.keys()), expected_fields)

    def test_recent_submissions_field(self):
        """Тест поля recent_submissions"""
        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )
        data = serializer.data

        self.assertIn('recent_submissions', data)
        self.assertIsInstance(data['recent_submissions'], list)

        # Должно быть не больше 4 посылок (как в коде)
        self.assertLessEqual(len(data['recent_submissions']), 4)

    def test_recent_submissions_ordered_by_date(self):
        """Тест сортировки последних посылок по дате"""
        from django.utils import timezone
        from datetime import timedelta

        submissions = Submission.objects.filter(user=self.user)
        now = timezone.now()

        for i, sub in enumerate(submissions):
            sub.submitted_at = now - timedelta(hours=i)
            sub.save()

        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )
        recent = serializer.data['recent_submissions']

        # Проверяем сортировку (от новых к старым)
        if len(recent) > 1:
            date0 = recent[0]['submitted_at']
            date1 = recent[1]['submitted_at']
            self.assertGreaterEqual(date0, date1)

    def test_recent_submissions_contains_correct_data(self):
        """Тест содержимого последних посылок"""
        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )
        recent = serializer.data['recent_submissions']

        if recent:
            submission = recent[0]
            # Проверяем поля из SubmissionReadSerializer
            expected_fields = {'id', 'problem_id', 'problem_title', 'file_url',
                               'submitted_at', 'status', 'code_size', 'metrics'}
            for field in expected_fields:
                self.assertIn(field, submission)

            # Проверяем типы данных
            self.assertIsInstance(submission['id'], int)
            self.assertIsInstance(submission['problem_id'], int)
            self.assertIsInstance(submission['problem_title'], str)
            self.assertIsInstance(submission['metrics'], dict)

            # Проверяем, что нет лишних полей
            self.assertNotIn('user', submission)
            self.assertNotIn('prevalidation', submission)

    def test_recent_submissions_with_file(self):
        """Тест последних посылок с файлом"""
        # Создаем посылку с файлом
        test_file = SimpleUploadedFile(
            'test.csv',
            b'col1,col2\n1,2\n3,4',
            content_type='text/csv'
        )

        Submission.objects.create(
            user=self.user,
            problem=self.problem,
            file=test_file,
            status='pending',
            metrics={'accuracy': 0.95}
        )

        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )
        recent = serializer.data['recent_submissions']

        # Находим созданную посылку
        submission_with_file = next(
            (s for s in recent if s['file_url'] is not None),
            None
        )

        if submission_with_file:
            self.assertIsNotNone(submission_with_file['file_url'])
            self.assertTrue(
                submission_with_file['file_url'].startswith('/media/submissions/') or
                'test.csv' in submission_with_file['file_url']
            )

    def test_empty_recent_submissions(self):
        """Тест пустого списка последних посылок"""
        Submission.objects.filter(user=self.user).delete()

        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )
        recent = serializer.data['recent_submissions']

        self.assertEqual(recent, [])

    def test_get_full_name_inheritance(self):
        """Тест наследования метода get_full_name"""
        serializer = ProfileDetailSerializer()
        full_name = serializer.get_full_name(self.profile)
        self.assertEqual(full_name, 'Петров Иван')

    def test_get_role_inheritance(self):
        """Тест наследования метода get_role"""
        serializer = ProfileDetailSerializer()
        role = serializer.get_role(self.profile)
        self.assertEqual(role, 'student')


class SubmissionSerializersTests(TestCase):
    """Тесты для сериализаторов посылок"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.problem = Problem.objects.create(
            title='Тестовая задача'
        )
        self.submission = Submission.objects.create(
            user=self.user,
            problem=self.problem,
            status='pending',
            metrics={'accuracy': 0.95}
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')

    def test_submission_read_serializer_fields(self):
        """Тест полей SubmissionReadSerializer"""
        serializer = SubmissionReadSerializer(
            instance=self.submission,
            context={'request': self.request}
        )
        data = serializer.data

        expected_fields = {'id', 'problem_id', 'problem_title', 'file_url',
                           'submitted_at', 'status', 'code_size', 'metrics'}
        self.assertEqual(set(data.keys()), expected_fields)

        self.assertEqual(data['problem_id'], self.problem.id)
        self.assertEqual(data['problem_title'], 'Тестовая задача')
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['metrics'], {'accuracy': 0.95})

    def test_submission_detail_serializer_fields(self):
        """Тест полей SubmissionDetailSerializer"""
        serializer = SubmissionDetailSerializer(
            instance=self.submission,
            context={'request': self.request}
        )
        data = serializer.data

        expected_fields = {'id', 'problem_id', 'problem_title', 'file_url',
                           'submitted_at', 'status', 'code_size', 'metrics',
                           'prevalidation'}
        self.assertEqual(set(data.keys()), expected_fields)

        # prevalidation может быть None
        self.assertIsNone(data['prevalidation'])

    def test_get_file_url_method(self):
        """Тест метода get_file_url"""
        serializer = SubmissionReadSerializer()

        # Без файла
        url = serializer.get_file_url(self.submission)
        self.assertIsNone(url)

        # С файлом
        test_file = SimpleUploadedFile(
            'test.csv',
            b'col1,col2\n1,2',
            content_type='text/csv'
        )
        self.submission.file = test_file
        self.submission.save()

        url = serializer.get_file_url(self.submission)
        self.assertIsNotNone(url)
        self.assertTrue(
            url.startswith('/media/submissions/') or
            'test.csv' in url
        )


class SubmissionReadSerializerMockTests(TestCase):
    """Тесты с моком для SubmissionReadSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.profile = Profile.objects.get(user=self.user)
        self.problem = Problem.objects.create(title='Test')
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')

    def test_recent_submissions_returns_correct_data(self):
        """Тест что метод get_recent_submissions возвращает правильные данные"""
        # Создаем посылку
        Submission.objects.create(
            user=self.user,
            problem=self.problem,
            status='pending',
            metrics={'accuracy': 0.95}
        )

        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )

        recent = serializer.get_recent_submissions(self.profile)

        self.assertIsNotNone(recent)
        self.assertIsInstance(recent, list)
        if recent:
            self.assertIn('id', recent[0])
            self.assertIn('problem_id', recent[0])
            self.assertIn('problem_title', recent[0])
            self.assertIn('status', recent[0])
            self.assertIn('metrics', recent[0])


class SerializerEdgeCasesTests(TestCase):
    """Тесты граничных случаев для сериализаторов"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.profile = Profile.objects.get(user=self.user)

    def test_user_serializer_with_empty_strings(self):
        """Тест UserSerializer с пустыми строками в имени"""
        self.user.first_name = ''
        self.user.last_name = ''
        self.user.save()

        serializer = UserSerializer(instance=self.user)
        data = serializer.data

        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['last_name'], '')
        self.assertEqual(data['full_name'], 'testuser')

    def test_profile_serializer_with_special_characters(self):
        """Тест ProfileSerializer с специальными символами в имени"""
        special_names = [
            ('John', 'Doe-Smith'),
            ('Анна-Мария', 'Иванова'),
            ('Jean', "D'Arc"),
            ('Jose', 'García'),
        ]

        for first, last in special_names:
            self.user.first_name = first
            self.user.last_name = last
            self.user.save()
            self.profile.refresh_from_db()

            serializer = ProfileSerializer(instance=self.profile)
            data = serializer.data

            self.assertEqual(data['first_name'], first)
            self.assertEqual(data['last_name'], last)
            self.assertEqual(data['full_name'], f"{last} {first}")

    def test_unicode_names(self):
        """Тест с юникод-символами в именах"""
        self.user.first_name = 'こんにちは'
        self.user.last_name = '世界'
        self.user.save()
        self.profile.refresh_from_db()

        serializer = ProfileSerializer(instance=self.profile)
        data = serializer.data

        self.assertEqual(data['first_name'], 'こんにちは')
        self.assertEqual(data['last_name'], '世界')
        self.assertEqual(data['full_name'], '世界 こんにちは')

    def test_very_long_names(self):
        """Тест с очень длинными именами"""
        long_first = 'А' * 100
        long_last = 'B' * 100

        self.user.first_name = long_first
        self.user.last_name = long_last
        self.user.save()
        self.profile.refresh_from_db()

        serializer = ProfileSerializer(instance=self.profile)
        data = serializer.data

        self.assertEqual(data['first_name'], long_first)
        self.assertEqual(data['last_name'], long_last)
        self.assertEqual(data['full_name'], f"{long_last} {long_first}")

    def test_avatar_url_with_request_context(self):
        """Тест получения URL аватара с контекстом запроса"""
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.user

        serializer = ProfileSerializer(
            instance=self.profile,
            context={'request': request}
        )

        url = serializer.get_avatar_url(self.profile)
        self.assertIsNone(url)