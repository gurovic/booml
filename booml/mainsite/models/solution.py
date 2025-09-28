from django.db import models
from django.conf import settings
from .problem import Problem
from django.db import models

class Solution(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solutions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    solved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-solved_at']

    def __str__(self):
        return f"{self.user.username} solved {self.problem.title}"
