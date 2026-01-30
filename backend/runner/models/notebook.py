from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
class Notebook(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='notebooks',
        null=True,
        blank=True,
    )
    problem = models.ForeignKey(
        'Problem',
        on_delete=models.SET_NULL,
        related_name='notebooks',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200, default="Новый блокнот")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['owner', 'problem'], name='notebook_owner_problem_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'problem'],
                condition=models.Q(owner__isnull=False) & models.Q(problem__isnull=False),
                name='unique_owner_problem_notebook'
            ),
        ]

    def __str__(self):
        return self.title