from django.db import models
from django.utils import timezone

class ProblemDescriptor(models.Model):
    """
    Stores the configuration (descriptor) for a problem.
    Usually loaded from JSON/YAML uploaded by the admin.
    """
    problem = models.OneToOneField(
        "Problem",
        on_delete=models.CASCADE,
        related_name="descriptor",
        db_index=True
    )

    # {
    #   "output_schema": ["id", "prediction"],
    #   "id_column": "id",
    #   "id_type": "int",
    #   "target_column": "prediction",
    #   "target_type": "float"
    #   "check_order": true,
    #   "min_rows": 1000,
    #   "max_rows": 100000
    # }
    
    config = models.JSONField(default=dict)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["competition"])]
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Descriptor for {self.problem}  ({self.updated_at})"