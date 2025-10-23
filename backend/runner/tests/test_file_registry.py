"""
Простой тест для file_registry
"""
from django.test import TestCase
from django.contrib.auth.models import User
from pathlib import Path
import tempfile
from runner.services.file_registry import register_file


class FileRegistryTest(TestCase):
    """Тест для регистрации файлов"""

    def test_register_file(self):
        """Проверяем, что файл регистрируется"""
        # Создаем пользователя
        user = User.objects.create_user(
            username='student',
            password='pass123'
        )
        
        # Создаем временный файл
        temp_dir = tempfile.mkdtemp()
        my_file = Path(temp_dir) / "myfile.txt"
        my_file.write_text("Hello!")
        
        # Регистрируем файл
        result = register_file(
            file_path=my_file,
            user=user,
            run_id="run1"
        )
        
        # Проверяем
        self.assertIsNotNone(result)
        self.assertEqual(result.file_name, "myfile.txt")
        self.assertEqual(result.user.username, "student")
        
        # Очистка
        import shutil
        shutil.rmtree(temp_dir)

