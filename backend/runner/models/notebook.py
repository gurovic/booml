from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
class Notebook(models.Model):
    class ComputeDevice(models.TextChoices):
        CPU = "cpu", "CPU"
        GPU = "gpu", "GPU"

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='notebooks',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200, default="Новый блокнот")
    compute_device = models.CharField(
        max_length=8,
        choices=ComputeDevice.choices,
        default=ComputeDevice.CPU,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title