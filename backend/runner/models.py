from django.db import models


class Report(models.Model):
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
    ]

    metric = models.FloatField(verbose_name="Метрика")
    log = models.TextField(verbose_name="Лог проверки")
    errors = models.TextField(verbose_name="Ошибки", blank=True)
    file_name = models.CharField(max_length=255, verbose_name="Имя файла")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Время отправки")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="success",
        verbose_name="Статус"
    )

    class Meta:
        verbose_name = "Отчёт"
        verbose_name_plural = "Отчёты"
        ordering = ['-submitted_at']  # Новые отчёты первыми

    def __str__(self):
        return f"{self.file_name} - {self.metric} - {self.status}"