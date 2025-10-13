from django.contrib.auth.models import User
from django.db import models
from notebook.runner.models.task import Task


class Notebook(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notebooks',
    )
    problem = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notebooks',
    )
    title = models.CharField(max_length=200, default="Новый блокнот")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
