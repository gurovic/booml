from django.db import models
from .notebook import Notebook


class Cell(models.Model):
    CELL_TYPES = [
        ('code', 'Код'),
        ('text', 'Текст'),
    ]
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, related_name='cells')
    cell_type = models.CharField(max_length=10, choices=CELL_TYPES, default='code')
    content = models.TextField(blank=True)
    output = models.TextField(blank=True)
    execution_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['execution_order']