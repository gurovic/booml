from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Problem(models.Model):
    title = models.CharField("Название", max_length=255)
    statement = models.TextField("Условие", blank=True)
    created_at = models.DateField("Дата создания", blank=True)
    rating = models.IntegerField("Рейтинг сложности", validators=[MinValueValidator(800), MaxValueValidator(3000)], default=800)
    train_data = models.FileField(
        "Файл с данными для тренировки модели",
        upload_to='problemtraindata/',
        blank=True,
        null=True
    )
    test_data = models.FileField(
        "Файл с данными для тестирования модели",
        upload_to='problemtestdata/',
        blank=True,
        null=True
    )
    answer_data = models.FileField(
        "Файл с правильными ответами на тест",
        upload_to='problemanswerdata/',
        blank=True,
        null=True
    )
    sample_submission_data = models.FileField(
        "Файл с примером правильного ответа",
        upload_to='problemsamplesubmissiondata/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title