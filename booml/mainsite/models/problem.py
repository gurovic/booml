from django.db import models


class Problem(models.Model):
    """
    Модель для хранения условий задач.
    Каждое поле соответствует разделу из условия задачи.
    """

    # Название задачи (например: "Сумма подотрезков")
    title = models.CharField("Название", max_length=255)

    # Полное текстовое описание задачи (формулировка и контекст)
    condition = models.TextField("Условие", blank=True)

    # Дата создания задач
    created_at = models.TextField("Дата создания", blank=True)

    def __str__(self):
        return self.title
