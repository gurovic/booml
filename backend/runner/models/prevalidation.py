from django.db import models
from django.utils import timezone


class PreValidation(models.Model):
    STATUS_CHOICES = [
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("warnings", "Warnings"),
    ]

    submission = models.OneToOneField(
        "Submission",
        on_delete=models.CASCADE,
        related_name="prevalidation"
    )

    valid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="failed")

    errors_count = models.PositiveIntegerField(default=0)
    warnings_count = models.PositiveIntegerField(default=0)
    rows_total = models.BigIntegerField(null=True, blank=True)

    unique_ids = models.BigIntegerField(null=True, blank=True)
    first_id = models.CharField(max_length=255, null=True, blank=True)
    last_id = models.CharField(max_length=255, null=True, blank=True)

    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    errors = models.JSONField(default=list)
    warnings = models.JSONField(default=list)
    stats = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["submission", "created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"PreValidation #{self.id} [{self.status}] for submission #{self.submission}"

    @property
    def is_valid(self) -> bool:
        """Backwards-compatible flag used across the codebase/tests."""
        if self.valid:
            return True
        return self.status in ("passed", "warnings")
