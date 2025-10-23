from django.db import models
from django.contrib.auth.models import User
import os


class UserFile(models.Model):
    """
    Модель для хранения файлов, созданных пользователем в результате выполнения кода
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_files")
    submission = models.ForeignKey("Submission", on_delete=models.SET_NULL, null=True, blank=True, related_name="output_files")
    
    # Информация о файле
    file = models.FileField(upload_to="user_files/")
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Дополнительная информация о файле
    run_id = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        if not self.file_name and self.file:
            self.file_name = os.path.basename(self.file.name)
        if not self.file_size and self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        """Возвращает размер файла в удобочитаемом формате"""
        size_kb = self.file_size / 1024
        if size_kb < 1024:
            return f"{size_kb:.2f} KB"
        size_mb = size_kb / 1024
        return f"{size_mb:.2f} MB"

    def __str__(self):
        return f"{self.file_name} ({self.user.username})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Файл пользователя"
        verbose_name_plural = "Файлы пользователей"
