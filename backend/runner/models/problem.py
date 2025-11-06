import markdown
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor

from django.utils.safestring import mark_safe

class Problem(models.Model):
    title = models.CharField("Название", max_length=255)
    statement = models.TextField("Условие", blank=True)
    created_at = models.DateField("Дата создания", auto_now_add=True)
    rating = models.IntegerField(
        "Рейтинг сложности",
        validators=[MinValueValidator(800), MaxValueValidator(3000)],
        default=800
    )

    def __str__(self):
        return self.title

    def render_statement(self):
        return mark_safe(markdown.markdown(
            self.statement,
            extensions=[
                "fenced_code",
                "tables",
                "md_in_html",
                "toc"
            ]
        ))