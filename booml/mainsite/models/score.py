from django.db import models
from mainsite.models import Submission

# Create your models here.

class Score(models.Model):
    status = models.SmallIntegerField(null=False)
    time = models.IntegerField(null=True)
    memory = models.BigIntegerField(null=True) # in KBs
    # metrics
    accuracy = models.FloatField(null=False)
    F1_score = models.FloatField(null=False)
    
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
