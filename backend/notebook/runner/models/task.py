from django.db import models


class Task(models.Model):
    title = models.CharField("Название", max_length=255)
    statement = models.TextField("Условие", blank=True)
    created_at = models.DateField("Дата создания", auto_now_add=True)

    def __str__(self) -> str:
        return self.title

