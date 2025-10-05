from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
import json


class CheckReport(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('partial_failure', 'Partial Failure'),
        ('critical_failure', 'Critical Failure'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    execution_time = models.FloatField(help_text="Execution time in seconds")
    system_version = models.CharField(max_length=50, default='1.0.0')
    context = models.JSONField(default=dict, encoder=DjangoJSONEncoder)

    class Meta:
        db_table = 'checker_reports'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Report {self.id} - {self.status} - {self.timestamp}"


class CheckMetrics(models.Model):
    report = models.OneToOneField(
        CheckReport,
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    total_checks = models.IntegerField(default=0)
    passed_checks = models.IntegerField(default=0)
    failed_checks = models.IntegerField(default=0)
    success_rate = models.FloatField(default=0.0)

    class Meta:
        db_table = 'checker_metrics'

    def __str__(self):
        return f"Metrics for Report {self.report.id}"


class CheckError(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    report = models.ForeignKey(
        CheckReport,
        on_delete=models.CASCADE,
        related_name='errors'
    )
    check_name = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    details = models.JSONField(default=dict, null=True, blank=True, encoder=DjangoJSONEncoder)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'checker_errors'
        ordering = ['-severity', 'check_name']

    def __str__(self):
        return f"{self.check_name} - {self.severity}"