from django.db import models
from django.utils import timezone

class ProblemDescriptor(models.Model):
    problem = models.ForeignKey("Problem", on_delete=models.CASCADE, related_name="descriptor", db_index=True)
    
    id_column = models.CharField(max_length=100, default="id")
    target_column = models.CharField(max_length=100, default="prediction")

    id_type = models.CharField(max_length=20, choices=[("int", "Integer"), ("str", "String")], default="int")
    target_type = models.CharField(max_length=20, choices=[("float", "Float"), ("int", "Integer"), ("str", "String")], default="float")
    
    check_order = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["problem"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Descriptor for {self.problem}, created at {self.created_at}"