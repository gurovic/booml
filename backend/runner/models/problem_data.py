from django.db import models
from django.utils import timezone
from functools import partial

def _problem_file_path(kind: str, instance, filename):
    return f"problem_data/{instance.problem_id}/{kind}/{filename}"

problem_train_path  = partial(_problem_file_path, "train")
problem_test_path   = partial(_problem_file_path, "test")
problem_sample_path = partial(_problem_file_path, "sample_submission")
problem_answer_path = partial(_problem_file_path, "answer")

class ProblemData(models.Model):
    problem = models.OneToOneField(
        "Problem",
        on_delete=models.CASCADE,
        related_name="data"
    )

    train_file = models.FileField(upload_to=problem_train_path, null=True, blank=True)
    test_file = models.FileField(upload_to=problem_test_path, null=True, blank=True)
    sample_submission_file = models.FileField(upload_to=problem_sample_path, null=True, blank=True)
    answer_file = models.FileField(upload_to=problem_answer_path, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["problem"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"ProblemData for {self.problem}"
