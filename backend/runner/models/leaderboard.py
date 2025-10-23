from django.db import models


class Leaderboard(models.Model):
    # Базовый минимум, чтобы модель существовала
    name = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Leaderboard #{self.pk}"
