from django.db import models

class ProblemData(models.Model):
    problem = models.OneToOneField(
        "Problem",  # связываем с моделью Problem
        on_delete=models.CASCADE,  # если задачу удалят — удалим и данные
        related_name="data"  # доступ из Problem через problem.data
    )

    # Файл с обучающими данными
    train_csv = models.FileField(
        upload_to="datasets/train/",
        blank=True,
        null=True,
        verbose_name="Train CSV"
    )

    # Файл с тестовыми данными
    test_csv = models.FileField(
        upload_to="datasets/test/",
        blank=True,
        null=True,
        verbose_name="Test CSV"
    )

    # Метрика для оценки (например, Accuracy, F1, RMSE)
    metric = models.CharField(
        max_length=50,
        choices=[
            ("accuracy", "Accuracy"),
            ("f1", "F1-score"),
            ("rmse", "RMSE"),
            ("mae", "MAE"),
        ],
        default="accuracy",
        verbose_name="Метрика"
    )

    def __str__(self):
        return f"ProblemData (метрика: {self.metric})"
