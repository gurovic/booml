from django.db import models
from .notebook import Notebook


class Cell(models.Model):
    CODE = "code"
    LATEX = "latex"
    TEXT = "text"
    TYPE_CHOICES = (
        (CODE, "Code"),
        (LATEX, "LaTeX"),
        (TEXT, "Text"),
    )

    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, related_name='cells')
    cell_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=CODE)
    content = models.TextField(blank=True)
    output = models.TextField(blank=True)
    execution_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['execution_order']