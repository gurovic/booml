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
                           'full_name', 'role', 'avatar', 'avatar_url',
                           'recent_submissions', 'activity_heatmap'}
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
            # Добавлено поле 'score'
            expected_fields = {'id', 'problem_id', 'problem_title', 'file_url',
                               'submitted_at', 'status', 'code_size', 'metrics', 'score'}
            for field in expected_fields:
                self.assertIn(field, submission)

            # Проверяем типы данных
            self.assertIsInstance(submission['id'], int)
            self.assertIsInstance(submission['problem_id'], int)
            self.assertIsInstance(submission['problem_title'], str)
            self.assertIsInstance(submission['metrics'], dict)

            # Проверяем, что score есть и это число или None
            self.assertIn('score', submission)
            if submission['score'] is not None:
                self.assertIsInstance(submission['score'], (int, float))

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

    def test_activity_heatmap_field_shape(self):
        """Тест структуры поля activity_heatmap"""
        from datetime import date, timedelta

        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )
        heatmap = serializer.data['activity_heatmap']

        expected_keys = {
            'start_date', 'end_date', 'period_type', 'selected_year', 'available_years',
            'total_submissions', 'active_days',
            'max_count', 'current_streak', 'best_streak', 'days'
        }
        self.assertEqual(set(heatmap.keys()), expected_keys)

        start_date = date.fromisoformat(heatmap['start_date'])
        end_date = date.fromisoformat(heatmap['end_date'])
        self.assertEqual(heatmap['period_type'], 'rolling_365')
        self.assertIsNone(heatmap['selected_year'])
        self.assertEqual(end_date - start_date, timedelta(days=364))
        self.assertEqual(len(heatmap['days']), 365)
        self.assertTrue(len(heatmap['available_years']) >= 1)

        first_day = heatmap['days'][0]
        self.assertIn('date', first_day)
        self.assertIn('count', first_day)
        self.assertIn('level', first_day)

    def test_activity_heatmap_aggregates_daily_counts(self):
        """Тест корректной агрегации активности по дням"""
        from datetime import datetime, time, timedelta
        from django.utils import timezone

        submissions = list(Submission.objects.filter(user=self.user).order_by('id'))
        tz = timezone.get_current_timezone()
        today = timezone.localdate()

        offsets = [0, 0, 1, 3, 3]
        for submission, days_ago in zip(submissions, offsets):
            target_day = today - timedelta(days=days_ago)
            submission.submitted_at = timezone.make_aware(
                datetime.combine(target_day, time(hour=12)),
                timezone=tz,
            )
            submission.save(update_fields=['submitted_at'])

        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )
        heatmap = serializer.data['activity_heatmap']
        count_by_date = {item['date']: item['count'] for item in heatmap['days']}

        self.assertEqual(heatmap['total_submissions'], 5)
        self.assertEqual(heatmap['active_days'], 3)
        self.assertEqual(heatmap['max_count'], 2)

        self.assertEqual(count_by_date[(today - timedelta(days=0)).isoformat()], 2)
        self.assertEqual(count_by_date[(today - timedelta(days=1)).isoformat()], 1)
        self.assertEqual(count_by_date[(today - timedelta(days=3)).isoformat()], 2)

    def test_activity_heatmap_respects_selected_year(self):
        """Тест выбора года для тепловой карты"""
        from datetime import datetime, time
        from django.utils import timezone

        Submission.objects.filter(user=self.user).delete()

        tz = timezone.get_current_timezone()
        current_year = timezone.localdate().year
        registration_year = current_year - 2
        requested_year = current_year - 1

        self.user.date_joined = timezone.make_aware(
            datetime(registration_year, 6, 1, 12, 0, 0),
            timezone=tz,
        )
        self.user.save(update_fields=['date_joined'])

        for day in [10, 11]:
            submission = Submission.objects.create(
                user=self.user,
                problem=self.problem,
                status='pending',
                metrics={'accuracy': 0.91}
            )
            submission.submitted_at = timezone.make_aware(
                datetime(requested_year, 5, day, 12, 0, 0),
                timezone=tz,
            )
            submission.save(update_fields=['submitted_at'])

        submission_current_year = Submission.objects.create(
            user=self.user,
            problem=self.problem,
            status='pending',
            metrics={'accuracy': 0.82}
        )
        submission_current_year.submitted_at = timezone.make_aware(
            datetime(current_year, 2, 1, 12, 0, 0),
            timezone=tz,
        )
        submission_current_year.save(update_fields=['submitted_at'])

        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request, 'activity_year': requested_year}
        )
        heatmap = serializer.data['activity_heatmap']

        self.assertEqual(heatmap['selected_year'], requested_year)
        self.assertEqual(heatmap['period_type'], 'year')
        self.assertEqual(
            heatmap['available_years'],
            [registration_year, registration_year + 1, current_year]
        )
        self.assertEqual(heatmap['total_submissions'], 2)

    def test_activity_heatmap_default_rolling_window_even_for_recent_user(self):
        """По умолчанию должен быть режим последних 365 дней, даже для новых пользователей"""
        from datetime import datetime
        from django.utils import timezone

        today = timezone.localdate()
        self.user.date_joined = timezone.make_aware(
            datetime(today.year, today.month, today.day, 12, 0, 0),
            timezone=timezone.get_current_timezone(),
        )
        self.user.save(update_fields=['date_joined'])

        serializer = ProfileDetailSerializer(
            instance=self.profile,
            context={'request': self.request}
        )
        heatmap = serializer.data['activity_heatmap']

        self.assertEqual(heatmap['period_type'], 'rolling_365')
        self.assertIsNone(heatmap['selected_year'])

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

        # Добавлено поле 'score'
        expected_fields = {'id', 'problem_id', 'problem_title', 'file_url',
                           'submitted_at', 'status', 'code_size', 'metrics', 'score'}
        self.assertEqual(set(data.keys()), expected_fields)

        self.assertEqual(data['problem_id'], self.problem.id)
        self.assertEqual(data['problem_title'], 'Тестовая задача')
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['metrics'], {'accuracy': 0.95})

        # Проверяем, что score есть и это число или None
        self.assertIn('score', data)
        if data['score'] is not None:
            self.assertIsInstance(data['score'], (int, float))

    def test_submission_detail_serializer_fields(self):
        """Тест полей SubmissionDetailSerializer"""
        serializer = SubmissionDetailSerializer(
            instance=self.submission,
            context={'request': self.request}
        )
        data = serializer.data

        # Добавлено поле 'score'
        expected_fields = {'id', 'problem_id', 'problem_title', 'file_url',
                           'submitted_at', 'status', 'code_size', 'metrics', 'score',
                           'prevalidation'}
        self.assertEqual(set(data.keys()), expected_fields)

        # prevalidation может быть None
        self.assertIsNone(data['prevalidation'])

        # Проверяем, что score есть и это число или None
        self.assertIn('score', data)
        if data['score'] is not None:
            self.assertIsInstance(data['score'], (int, float))

    def test_get_score_method(self):
        """Тест метода get_score"""
        serializer = SubmissionReadSerializer()

        # Проверяем, что метод возвращает число или None
        score = serializer.get_score(self.submission)
        if score is not None:
            self.assertIsInstance(score, (int, float))

        # Создаем посылку с другими метриками
        submission2 = Submission.objects.create(
            user=self.user,
            problem=self.problem,
            status='accepted',
            metrics={'accuracy': 0.85, 'f1': 0.78}
        )
        score2 = serializer.get_score(submission2)
        if score2 is not None:
            self.assertIsInstance(score2, (int, float))

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
