from django.db import models
from django.utils import timezone

class ProblemData(models.Model):
    problem = models.ForeignKey(
        "Problem",
        on_delete=models.CASCADE,
        related_name="data"
    )

    train_file = models.FileField(upload_to=f"problem_data/{problem.id}/train/", null=True, blank=True)
    test_file = models.FileField(upload_to=f"problem_data/{problem.id}/test/", null=True, blank=True)
    sample_submission_file = models.FileField(upload_to=f"problem_data/{problem.id}/sample_submission/", null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["problem"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"ProblemData for {self.problem}"
