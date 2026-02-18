from django.db import models
from django.contrib.auth.models import User


class Submission(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_ACCEPTED = "accepted"
    STATUS_FAILED = "failed"
    STATUS_VALIDATED = "validated"
    STATUS_VALIDATION_ERROR = "validation_error"
    STATUS_CHOICES = [
        ("pending", "⏳ В очереди"),
        ("running", "🏃 Выполняется"),
        ("accepted", "✅ Протестировано"),
        ("failed", "❌ Ошибка"),
        ("validation_error", "⚠️ Ошибка валидации"),
        ("validated", "✅ Валидировано"),
    ]

    SOURCE_FILE = "file"
    SOURCE_TEXT = "text"

    SOURCE_CHOICES = [
        (SOURCE_FILE, "File upload"),
        (SOURCE_TEXT, "Text input"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    problem = models.ForeignKey("Problem", on_delete=models.CASCADE, related_name="submissions", null=True)
    file = models.FileField(upload_to="submissions/", null = True, blank = True)
    raw_text = models.TextField(null=True, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_FILE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    code_size = models.PositiveIntegerField(default=0)
    metrics = models.JSONField(null=True, blank=True)  # {"accuracy": 0.87, "f1": 0.65}
    
    @property
    def file_path(self) -> str:
        """Алиас для совместимости с validation_service."""
        if self.file:
            return self.file.path
        return None

    def save(self, *args, **kwargs):
        if self.file and not self.code_size:
            self.code_size = self.file.size

        elif self.raw_text and not self.code_size:
            self.code_size = len(self.raw_text.encode("utf-8"))

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.problem} [{self.status}]"
