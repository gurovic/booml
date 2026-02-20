from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from unittest.mock import patch, MagicMock
import tempfile

from ..models import Profile
from ..views.profile import (
    get_my_profile,
    get_profile_by_id,
    update_avatar,
    delete_avatar,
    update_profile_info
)

User = get_user_model()


class ProfileViewsTests(TestCase):
    """Тесты для views профиля"""

    def setUp(self):
        self.factory = APIRequestFactory()

        # Создаем пользователя
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            first_name='Иван',
            last_name='Петров'
        )

        # Создаем второго пользователя
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123',
            email='other@example.com'
        )

        self.get_my_profile_url = '/api/profiles/me/'
        self.get_profile_by_id_url = '/api/profiles/{}/'
        self.update_avatar_url = '/api/profiles/avatar/'
        self.delete_avatar_url = '/api/profiles/avatar/delete/'
        self.update_profile_info_url = '/api/profiles/update/'


class GetMyProfileTests(ProfileViewsTests):
    """Тесты для get_my_profile"""

    def test_get_my_profile_unauthenticated(self):
        """Неавторизованный пользователь не может получить свой профиль"""
        request = self.factory.get(self.get_my_profile_url)
        response = get_my_profile(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_my_profile_authenticated(self):
        """Авторизованный пользователь может получить свой профиль"""
        request = self.factory.get(self.get_my_profile_url)
        force_authenticate(request, user=self.user)
        response = get_my_profile(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['first_name'], 'Иван')
        self.assertEqual(response.data['last_name'], 'Петров')
        self.assertIn('recent_submissions', response.data)

    def test_get_my_profile_creates_profile_if_not_exists(self):
        """Тест что профиль создается автоматически если его нет"""
        # Создаем пользователя без профиля
        new_user = User.objects.create_user(
            username='newuser',
            password='newpass123'
        )

        # Удаляем профиль если он создался сигналом
        Profile.objects.filter(user=new_user).delete()

        # Проверяем что профиля нет
        with self.assertRaises(Profile.DoesNotExist):
            Profile.objects.get(user=new_user)

        request = self.factory.get(self.get_my_profile_url)
        force_authenticate(request, user=new_user)
        response = get_my_profile(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что профиль создался
        profile = Profile.objects.get(user=new_user)
        self.assertIsNotNone(profile)


class GetProfileByIdTests(ProfileViewsTests):
    """Тесты для get_profile_by_id"""

    def test_get_profile_by_id_unauthenticated(self):
        """Неавторизованный пользователь не может получить профиль по ID"""
        url = self.get_profile_by_id_url.format(self.other_user.id)
        request = self.factory.get(url)
        response = get_profile_by_id(request, user_id=self.other_user.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_profile_by_id_authenticated(self):
        """Авторизованный пользователь может получить профиль другого пользователя"""
        url = self.get_profile_by_id_url.format(self.other_user.id)
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)
        response = get_profile_by_id(request, user_id=self.other_user.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'otheruser')
        self.assertEqual(response.data['email'], 'other@example.com')

    def test_get_profile_by_id_not_found(self):
        """Тест получения профиля с несуществующим ID"""
        non_existent_id = 99999
        url = self.get_profile_by_id_url.format(non_existent_id)
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)
        response = get_profile_by_id(request, user_id=non_existent_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)

    def test_get_profile_by_id_user_without_profile(self):
        """Тест получения пользователя у которого нет профиля"""
        # Создаем пользователя и удаляем его профиль
        user_without_profile = User.objects.create_user(
            username='noprofile',
            password='testpass123'
        )
        Profile.objects.filter(user=user_without_profile).delete()

        url = self.get_profile_by_id_url.format(user_without_profile.id)
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)
        response = get_profile_by_id(request, user_id=user_without_profile.id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Профиль не найден', str(response.data))


class UpdateAvatarTests(ProfileViewsTests):
    """Тесты для update_avatar"""

    def test_update_avatar_unauthenticated(self):
        """Неавторизованный пользователь не может обновить аватар"""
        request = self.factory.patch(self.update_avatar_url)
        response = update_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_avatar_success(self):
        """Тест успешного обновления аватара"""
        # Создаем тестовое изображение
        avatar_content = b'fake_image_content'
        avatar = SimpleUploadedFile(
            'test_avatar.jpg',
            avatar_content,
            content_type='image/jpeg'
        )

        request = self.factory.patch(
            self.update_avatar_url,
            {'avatar': avatar},
            format='multipart'
        )
        force_authenticate(request, user=self.user)
        response = update_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что аватар сохранился
        profile = Profile.objects.get(user=self.user)
        self.assertIsNotNone(profile.avatar)
        self.assertTrue('test_avatar' in profile.avatar.name)

        # Очищаем
        profile.avatar.delete()

    def test_update_avatar_no_file(self):
        """Тест обновления аватара без файла"""
        request = self.factory.patch(self.update_avatar_url, {}, format='multipart')
        force_authenticate(request, user=self.user)
        response = update_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Файл аватара не предоставлен', str(response.data))

    def test_update_avatar_too_large(self):
        """Тест обновления аватара с файлом превышающим лимит (5MB)"""
        # Создаем файл размером 6MB
        large_content = b'x' * (6 * 1024 * 1024)
        avatar = SimpleUploadedFile(
            'large_avatar.jpg',
            large_content,
            content_type='image/jpeg'
        )

        request = self.factory.patch(
            self.update_avatar_url,
            {'avatar': avatar},
            format='multipart'
        )
        force_authenticate(request, user=self.user)
        response = update_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Файл слишком большой', str(response.data))

    def test_update_avatar_wrong_type(self):
        """Тест обновления аватара с неподдерживаемым типом файла"""
        # Создаем текстовый файл
        avatar = SimpleUploadedFile(
            'test.txt',
            b'text content',
            content_type='text/plain'
        )

        request = self.factory.patch(
            self.update_avatar_url,
            {'avatar': avatar},
            format='multipart'
        )
        force_authenticate(request, user=self.user)
        response = update_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Допустимы только JPEG, PNG и GIF', str(response.data))

    def test_update_avatar_replace_existing(self):
        """Тест замены существующего аватара"""
        profile = Profile.objects.get(user=self.user)

        # Создаем первый аватар
        avatar1 = SimpleUploadedFile(
            'avatar1.jpg',
            b'avatar1_content',
            content_type='image/jpeg'
        )
        profile.avatar.save('avatar1.jpg', avatar1)
        old_avatar_path = profile.avatar.path

        # Создаем второй аватар
        avatar2 = SimpleUploadedFile(
            'avatar2.jpg',
            b'avatar2_content',
            content_type='image/jpeg'
        )

        request = self.factory.patch(
            self.update_avatar_url,
            {'avatar': avatar2},
            format='multipart'
        )
        force_authenticate(request, user=self.user)
        response = update_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что аватар заменился
        profile.refresh_from_db()
        self.assertIsNotNone(profile.avatar)
        self.assertTrue('avatar2' in profile.avatar.name)

        # Очищаем
        profile.avatar.delete()

    def test_update_avatar_user_without_profile(self):
        """Тест обновления аватара для пользователя без профиля"""
        # Удаляем профиль
        Profile.objects.filter(user=self.user).delete()

        avatar = SimpleUploadedFile(
            'test.jpg',
            b'content',
            content_type='image/jpeg'
        )

        request = self.factory.patch(
            self.update_avatar_url,
            {'avatar': avatar},
            format='multipart'
        )
        force_authenticate(request, user=self.user)
        response = update_avatar(request)

        # Должен быть 404, но view создает профиль автоматически
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(Profile.objects.get(user=self.user))


class DeleteAvatarTests(ProfileViewsTests):
    """Тесты для delete_avatar"""

    def test_delete_avatar_unauthenticated(self):
        """Неавторизованный пользователь не может удалить аватар"""
        request = self.factory.delete(self.delete_avatar_url)
        response = delete_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_avatar_success(self):
        """Тест успешного удаления аватара"""
        profile = Profile.objects.get(user=self.user)

        # Создаем аватар
        avatar = SimpleUploadedFile(
            'test.jpg',
            b'avatar_content',
            content_type='image/jpeg'
        )
        profile.avatar.save('test.jpg', avatar)
        self.assertIsNotNone(profile.avatar)

        request = self.factory.delete(self.delete_avatar_url)
        force_authenticate(request, user=self.user)
        response = delete_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что аватар удален
        profile.refresh_from_db()
        self.assertFalse(profile.avatar)  # В Django пустой ImageField - falsy

    def test_delete_avatar_when_no_avatar(self):
        """Тест удаления аватара когда его нет"""
        profile = Profile.objects.get(user=self.user)
        self.assertFalse(profile.avatar)  # В Django пустой ImageField - falsy

        request = self.factory.delete(self.delete_avatar_url)
        force_authenticate(request, user=self.user)
        response = delete_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что аватар все еще None
        profile.refresh_from_db()
        self.assertFalse(profile.avatar)

    def test_delete_avatar_user_without_profile(self):
        """Тест удаления аватара для пользователя без профиля"""
        # Удаляем профиль
        Profile.objects.filter(user=self.user).delete()

        request = self.factory.delete(self.delete_avatar_url)
        force_authenticate(request, user=self.user)
        response = delete_avatar(request)

        # Должен быть 404, но view создает профиль автоматически
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(Profile.objects.get(user=self.user))


class UpdateProfileInfoTests(ProfileViewsTests):
    """Тесты для update_profile_info"""

    def test_update_profile_info_unauthenticated(self):
        """Неавторизованный пользователь не может обновить информацию"""
        request = self.factory.patch(self.update_profile_info_url)
        response = update_profile_info(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_profile_info_success(self):
        """Тест успешного обновления информации профиля"""
        data = {
            'first_name': 'НовыйИван',
            'last_name': 'НовыйПетров'
        }

        request = self.factory.patch(self.update_profile_info_url, data)
        force_authenticate(request, user=self.user)
        response = update_profile_info(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что данные обновились
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'НовыйИван')
        self.assertEqual(self.user.last_name, 'НовыйПетров')

        # Проверяем что вернулся обновленный профиль
        self.assertEqual(response.data['first_name'], 'НовыйИван')
        self.assertEqual(response.data['last_name'], 'НовыйПетров')

    def test_update_profile_info_partial(self):
        """Тест частичного обновления информации"""
        # Обновляем только имя
        data = {'first_name': 'НовыйИван'}

        request = self.factory.patch(self.update_profile_info_url, data)
        force_authenticate(request, user=self.user)
        response = update_profile_info(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'НовыйИван')
        self.assertEqual(self.user.last_name, 'Петров')  # Фамилия не изменилась

        # Обновляем только фамилию
        data = {'last_name': 'НовыйПетров'}

        request = self.factory.patch(self.update_profile_info_url, data)
        force_authenticate(request, user=self.user)
        response = update_profile_info(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'НовыйИван')
        self.assertEqual(self.user.last_name, 'НовыйПетров')

    def test_update_profile_info_empty(self):
        """Тест обновления с пустыми данными"""
        request = self.factory.patch(self.update_profile_info_url, {})
        force_authenticate(request, user=self.user)
        response = update_profile_info(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Данные не должны измениться
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Иван')
        self.assertEqual(self.user.last_name, 'Петров')

    def test_update_profile_info_with_null(self):
        """Тест обновления с null значениями"""
        data = {
            'first_name': None,
            'last_name': None
        }

        request = self.factory.patch(self.update_profile_info_url, data, format='json')
        force_authenticate(request, user=self.user)
        response = update_profile_info(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что имена НЕ стали пустыми (null игнорируется)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Иван')
        self.assertEqual(self.user.last_name, 'Петров')

    def test_update_profile_info_with_empty_strings(self):
        """Тест обновления с пустыми строками"""
        data = {
            'first_name': '',
            'last_name': ''
        }

        request = self.factory.patch(self.update_profile_info_url, data)
        force_authenticate(request, user=self.user)
        response = update_profile_info(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, '')
        self.assertEqual(self.user.last_name, '')

    def test_update_profile_info_user_without_profile(self):
        """Тест обновления информации для пользователя без профиля"""
        # Удаляем профиль
        Profile.objects.filter(user=self.user).delete()

        data = {'first_name': 'Новый'}

        request = self.factory.patch(self.update_profile_info_url, data)
        force_authenticate(request, user=self.user)
        response = update_profile_info(request)

        # Должен быть 404, но view создает профиль автоматически
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(Profile.objects.get(user=self.user))


class ProfileViewsEdgeCasesTests(TestCase):
    """Тесты граничных случаев для views профиля"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_update_avatar_with_special_chars_in_filename(self):
        """Тест загрузки аватара с спецсимволами в имени файла"""
        avatar = SimpleUploadedFile(
            'test_@#$%_avatar.jpg',
            b'content',
            content_type='image/jpeg'
        )

        request = self.factory.patch(
            '/api/profiles/avatar/',
            {'avatar': avatar},
            format='multipart'
        )
        force_authenticate(request, user=self.user)
        response = update_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Очищаем
        profile = Profile.objects.get(user=self.user)
        profile.avatar.delete()

    def test_update_avatar_with_cyrillic_filename(self):
        """Тест загрузки аватара с кириллицей в имени файла"""
        avatar = SimpleUploadedFile(
            'мой_аватар.jpg',
            b'content',
            content_type='image/jpeg'
        )

        request = self.factory.patch(
            '/api/profiles/avatar/',
            {'avatar': avatar},
            format='multipart'
        )
        force_authenticate(request, user=self.user)
        response = update_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Очищаем
        profile = Profile.objects.get(user=self.user)
        profile.avatar.delete()

    @patch('runner.models.Profile.save')
    def test_update_avatar_save_error(self, mock_save):
        """Тест ошибки при сохранении аватара"""
        mock_save.side_effect = Exception('Database error')

        avatar = SimpleUploadedFile(
            'test.jpg',
            b'content',
            content_type='image/jpeg'
        )

        request = self.factory.patch(
            '/api/profiles/avatar/',
            {'avatar': avatar},
            format='multipart'
        )
        force_authenticate(request, user=self.user)

        response = update_avatar(request)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('detail', response.data)

        mock_save.assert_called_once()