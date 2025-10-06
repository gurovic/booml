# models.py
from django.db import models

class CodeRun(models.Model):
    run_id = models.CharField(max_length=64, unique=True)
    code = models.TextField()
    lang = models.CharField(max_length=24, default='python')
    created_at = models.DateTimeField(auto_now_add=True)
    result = models.TextField(blank=True, null=True)      # stdout
    stderr = models.TextField(blank=True, null=True)      # stderr
    elapsed_ms = models.IntegerField(default=0)
    exit_code = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.run_id} ({self.lang})"
