from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.conf import settings

from ..models.problem_data import ProblemData
from ..models.problem_desriptor import ProblemDescriptor

try:
    import markdown  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    markdown = None

class Problem(models.Model):
    title = models.CharField("Название", max_length=255)
    statement = models.TextField("Условие", blank=True)
    created_at = models.DateField("Дата создания", auto_now_add=True)
    rating = models.IntegerField(
        "Рейтинг сложности",
        validators=[MinValueValidator(800), MaxValueValidator(3000)],
        default=800,
    )
    is_published = models.BooleanField("Опубликована", default=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор",
        on_delete=models.SET_NULL,
        related_name="problems",
        default=None,
        null=True,
    )

    def __str__(self):
        return self.title

    def render_statement(self):
        if markdown:
            html = markdown.markdown(
                self.statement,
                extensions=["fenced_code", "tables", "md_in_html", "toc"],
            )
        else:
            # Fallback to escaped plain text if markdown package is unavailable.
            html = escape(self.statement).replace("\n", "<br>")
        return mark_safe(html)
