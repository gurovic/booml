from django.db import models
from django.utils import timezone

class SubmissionPreValidation(models.Model):
    # Status choices for the validation result
    STATUS_CHOICES = [
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("warnings", "Warnings"),
    ]

    # ForeignKey to Submission model (replace app label in service when resolving)
    submission = models.ForeignKey(
        "Submission",
        on_delete=models.CASCADE,
        related_name="validations",
        db_index=True
    )

    # Basic result flags
    valid = models.BooleanField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    # Counters
    errors_count = models.PositiveIntegerField(default=0)
    warnings_count = models.PositiveIntegerField(default=0)

    # Aggregated stats / summary fields
    rows_total = models.BigIntegerField(null=True, blank=True)
    unique_ids = models.BigIntegerField(null=True, blank=True)
    first_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    last_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    # JSON blobs for additional metadata and detailed lists
    file_info = models.JSONField(default=dict, help_text="filename, path, size, encoding, delimiter, ...")
    descriptor = models.JSONField(default=dict, help_text="snapshot of competition descriptor at validation time")
    stats = models.JSONField(default=dict, help_text="rows_processed, duplicates, missing_ids, ...")
    errors = models.JSONField(default=list, help_text="list of error messages (short)")
    warnings = models.JSONField(default=list, help_text="list of warnings (short)")

    # Timestamp
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        # index on (submission, created_at) is useful to fetch latest validations per submission
        indexes = [
            models.Index(fields=["submission", "created_at"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Validation #{self.id} for Submission {self.submission_id} [{self.status}]"

    # -------------------------------
    # Convenience methods for mutation
    # -------------------------------
    def append_error(self, message: str, max_errors: int = 50, save: bool = False):
        """
        Append an error message to the errors list and update errors_count.
        - max_errors: maximum number of error messages to keep in the JSON field.
        - save: if True, persist the model (update_fields used).
        """
        errs = list(self.errors or [])
        if len(errs) < max_errors:
            errs.append(message)
        # If we've reached the limit, additional messages are dropped (caller may log).
        self.errors = errs
        self.errors_count = len(errs)
        if save:
            try:
                self.save(update_fields=["errors", "errors_count"])
            except Exception:
                # Do not raise on save errors here; caller should handle/log if needed.
                pass

    def append_warning(self, message: str, max_warnings: int = 50, save: bool = False):
        """
        Append a warning message to the warnings list and update warnings_count.
        """
        warns = list(self.warnings or [])
        if len(warns) < max_warnings:
            warns.append(message)
        self.warnings = warns
        self.warnings_count = len(warns)
        if save:
            try:
                self.save(update_fields=["warnings", "warnings_count"])
            except Exception:
                pass

    def sync_counts(self, save: bool = False):
        """
        Synchronize numeric counters with the actual lists.
        Useful if errors/warnings changed externally.
        """
        self.errors_count = len(self.errors or [])
        self.warnings_count = len(self.warnings or [])
        if save:
            try:
                self.save(update_fields=["errors_count", "warnings_count"])
            except Exception:
                pass

    def add_stats(self, extra: dict, save: bool = False):
        """
        Merge extra stats into the stats JSONField.
        """
        s = dict(self.stats or {})
        s.update(extra or {})
        self.stats = s
        if save:
            try:
                self.save(update_fields=["stats"])
            except Exception:
                pass

    def finalize(self, *, valid: bool, status: str, duration_ms: int = None, save: bool = True):
        """
        Finalize the validation: set valid/status/duration and sync counts.
        By default it saves the model.
        """
        self.valid = valid
        self.status = status
        if duration_ms is not None:
            self.duration_ms = duration_ms
        # Ensure counters match current lists
        self.sync_counts(save=False)
        if save:
            # Persist full object for simplicity and correctness.
            try:
                self.save()
            except Exception:
                # Do not raise from finalize; caller handles unexpected exceptions/logging.
                pass
