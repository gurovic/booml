from django.db import models
from django.contrib.auth.models import User

class Submission(models.Model):
    STATUS_CHOICES = [
        ("pending", "⏳ В очереди"),
        ("running", "🏃 Выполняется"),
        ("accepted", "✅ Принято"),
        ("failed", "❌ Ошибка"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    problem = models.ForeignKey("Problem", on_delete=models.CASCADE, related_name="submissions")
    file = models.FileField(upload_to="submissions/")
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    code_size = models.PositiveIntegerField(default=0)
    metrics = models.JSONField(null=True, blank=True)  # {"accuracy": 0.87, "f1": 0.65}
    
    def save(self, *args, **kwargs):
        if self.file and not self.code_size:
            try:
                self.code_size = self.file.size
            except Exception:
                self.code_size = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.problem} ({self.score})"
