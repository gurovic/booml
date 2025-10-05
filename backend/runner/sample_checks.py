import psutil
import requests

def check_disk_space():
    """Проверка свободного места на диске"""
    disk_usage = psutil.disk_usage('/')
    free_percent = (disk_usage.free / disk_usage.total) * 100
    return free_percent > 10  # Минимум 10% свободного места

def check_memory_usage():
    """Проверка использования памяти"""
    memory = psutil.virtual_memory()
    return memory.percent < 90  # Максимум 90% использования

def check_network_connectivity():
    """Проверка сетевого соединения"""
    try:
        response = requests.get('https://google.com', timeout=5)
        return response.status_code == 200
    except:
        return False

def check_database_connection():
    """Проверка подключения к базе данных"""
    try:
        from django.db import connection
        connection.ensure_connection()
        return True
    except:
        return False

# Регистрация проверок
from .checker_service import checker_service

checker_service.register_check("disk_space", check_disk_space)
checker_service.register_check("memory_usage", check_memory_usage)
checker_service.register_check("network_connectivity", check_network_connectivity)
checker_service.register_check("database_connection", check_database_connection)