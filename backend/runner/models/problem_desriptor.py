from django.db import models
from django.utils import timezone

class ProblemDescriptor(models.Model):
    problem = models.OneToOneField("Problem", on_delete=models.CASCADE, related_name="descriptor", db_index=True)

    id_column = models.CharField(max_length=100, default="id")
    target_column = models.CharField(max_length=100, default="prediction")
    metric = models.CharField(max_length=50, blank=True, default="")

    id_type = models.CharField(max_length=20, choices=[("int", "Integer"), ("str", "String")], default="int")
    target_type = models.CharField(max_length=20, choices=[("float", "Float"), ("int", "Integer"), ("str", "String")],
                                   default="float")

    check_order = models.BooleanField(default=False)
    metric_name = models.CharField(max_length=100, default="rmse")
    metric_code = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["problem"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Descriptor for {self.problem}, created at {self.created_at}"

    @property
    def output_columns(self):
        """
        List of submission columns that should be validated.
        Defaults to the primary target column to keep callers simple.
        """
        return [self.target_column] if self.target_column else []

    def has_custom_metric(self) -> bool:
        return bool((self.metric_code or "").strip())