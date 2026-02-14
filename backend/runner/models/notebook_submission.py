from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class NotebookSubmission(models.Model):
    """
    Submission for notebook-based contests.
    Links a user's notebook to a contest and tracks checking status.
    """
    
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_ACCEPTED = "accepted"
    STATUS_FAILED = "failed"
    STATUS_VALIDATION_ERROR = "validation_error"
    STATUS_VALIDATED = "validated"
    STATUS_CHOICES = [
        ("pending", "⏳ В очереди"),
        ("running", "🏃 Выполняется"),
        ("accepted", "✅ Протестировано"),
        ("failed", "❌ Ошибка"),
        ("validation_error", "⚠️ Ошибка валидации"),
        ("validated", "✅ Валидировано"),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notebook_submissions"
    )
    contest = models.ForeignKey(
        "Contest",
        on_delete=models.CASCADE,
        related_name="notebook_submissions"
    )
    notebook = models.ForeignKey(
        "Notebook",
        on_delete=models.CASCADE,
        related_name="contest_submissions"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    # Store metrics for each task cell: {cell_id: {"score": 1.0, "metric": "csv_match"}}
    metrics = models.JSONField(null=True, blank=True)
    # Overall score (e.g., average or sum of all cell scores)
    total_score = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["user", "contest"], name="notebook_sub_user_contest_idx"),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Contest {self.contest.id} [{self.status}]"
