from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    data = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.title