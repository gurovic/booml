from django.db import models
from django.contrib.auth.models import User


class Notebook(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notebooks')
    title = models.CharField(max_length=200, default="Новый блокнот")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
