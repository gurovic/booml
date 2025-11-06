from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Task(models.Model):
    title = models.CharField("Название", max_length=255)
    statement = models.TextField("Условие", blank=True)
    created_at = models.DateField("Дата создания", blank=True)
    rating = models.IntegerField("Рейтинг сложности", validators=[MinValueValidator(800), MaxValueValidator(3000)], default=800)
    train_data = models.FileField(
        "Файл с данными для тренировки модели",
        upload_to='tasktraindata/',
        blank=True,
        null=True
    )
    test_data = models.FileField(
        "Файл с данными для тестирования модели",
        upload_to='tasktestdata/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title