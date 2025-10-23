"""
Сервис для регистрации файлов, созданных в результате выполнения кода
"""
import os
from pathlib import Path
from typing import Optional, List
from django.core.files import File
from django.contrib.auth.models import User
from ..models import UserFile, Submission


def register_file(
    file_path: Path,
    user: User,
    run_id: str,
    submission: Optional[Submission] = None,
    description: str = ""
) -> Optional[UserFile]:
    """
    Регистрирует файл в системе UserFile
    
    Args:
        file_path: Путь к файлу
        user: Пользователь, создавший файл
        run_id: ID запуска кода
        submission: Связанная посылка (опционально)
        description: Описание файла
    
    Returns:
        UserFile объект или None в случае ошибки
    """
    try:
        if not file_path.exists():
            return None
            
        # Получаем информацию о файле
        file_name = file_path.name
        file_size = file_path.stat().st_size
        
        # Создаем Django File объект
        with open(file_path, 'rb') as f:
            django_file = File(f, name=file_name)
            
            # Создаем запись UserFile
            user_file = UserFile.objects.create(
                user=user,
                submission=submission,
                file=django_file,
                file_name=file_name,
                file_size=file_size,
                run_id=run_id,
                description=description
            )
            
        return user_file
        
    except Exception as e:
        print(f"Ошибка регистрации файла {file_path}: {e}")
        return None


def register_files_from_directory(
    run_dir: Path,
    user: User,
    run_id: str,
    submission: Optional[Submission] = None
) -> List[UserFile]:
    """
    Регистрирует все файлы из директории выполнения
    
    Args:
        run_dir: Директория выполнения кода
        user: Пользователь
        run_id: ID запуска
        submission: Связанная посылка (опционально)
    
    Returns:
        Список созданных UserFile объектов
    """
    registered_files = []
    
    if not run_dir.exists():
        return registered_files
    
    # Исключаем служебные файлы
    excluded_files = {'main.py', '__pycache__', '.pyc', '.pyo'}
    
    for file_path in run_dir.iterdir():
        if file_path.is_file() and file_path.name not in excluded_files:
            user_file = register_file(
                file_path=file_path,
                user=user,
                run_id=run_id,
                submission=submission
            )
            if user_file:
                registered_files.append(user_file)
    
    return registered_files
