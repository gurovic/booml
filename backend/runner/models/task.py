from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Task(models.Model):
    title = models.CharField("Название", max_length=255)
    statement = models.TextField("Условие", blank=True)
    created_at = models.DateField("Дата создания", blank=True)
    rating = models.IntegerField("Рейтинг сложности", validators=[MinValueValidator(800), MaxValueValidator(3000)], default=800)
    data = models.FileField(
        "Файл с данными",
        upload_to='taskdata/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title