from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor


class Problem(models.Model):
    title = models.CharField("Название", max_length=255)
    statement = models.TextField("Условие", blank=True)
    created_at = models.DateField("Дата создания", blank=True)
    rating = models.IntegerField("Рейтинг сложности", validators=[MinValueValidator(800), MaxValueValidator(3000)], default=800)
    problem_data = models.OneToOneField(ProblemData, on_delete=models.CASCADE, related_name="problem")
    problem_descriptor = models.OneToOneField(ProblemDescriptor, on_delete=models.CASCADE, related_name="problem")

    def __str__(self):
        return self.title