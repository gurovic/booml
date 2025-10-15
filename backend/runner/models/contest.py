from django.db import models
from django.db.models import CharField, IntegerField, DateField, BooleanField

class Contest(models.Model):
  tasks = models.ManyToManyField("Task", null=True)
  source = CharField()
  _type = IntegerField(db_column="type", null=True)
  difficulty = IntegerField(null=True)
  start_time = DateField()
  duration = IntegerField(null=True)
  
  STATUS_CHOICES = {
    "going": "user",
    "after-soluting": "дорешка"
  }
  
  status = CharField(choices=STATUS_CHOICES)
  
  open = BooleanField()
  leaderBoard = models.ForeignKey("Leaderboard", on_delete=models.CASCADE)