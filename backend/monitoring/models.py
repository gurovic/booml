from django.db import models
from datetime import datetime, timedelta


class SystemMetric(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    cpu_percent = models.FloatField()
    memory_percent = models.FloatField()
    disk_percent = models.FloatField()

    class Meta:
        db_table = 'system_metrics'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp}: CPU {self.cpu_percent}%, Memory {self.memory_percent}%, Disk {self.disk_percent}%"

    @classmethod
    def get_recent_metrics(cls, minutes=30):
        """Получить метрики за последние N минут"""
        # Возвращаем все записи без ограничения по времени для отладки
        return cls.objects.all().order_by('-timestamp')