from django.db import models
from django.db.models import CharField, IntegerField, DateField, ManyToManyField

class Contest(models.Model):
  tasks = ManyToManyField("Task", blank=True)
  source = CharField()
  _type = IntegerField(db_column="type", blank=True)
  difficulty = IntegerField(blank=True)
  start_time = DateField()
  duration = IntegerField(blank=True)
  
  STATUS_CHOICES = {
    0: "going",
    1: "after-solving"
  }
  status = IntegerField(choices=STATUS_CHOICES, default=0)
  
  OPEN_CHOICES = {
    0: "closed",
    1: "opened"
  }
  open = IntegerField(default=0, choices=OPEN_CHOICES)
  
  leaderBoard = models.ForeignKey("Leaderboard", on_delete=models.CASCADE)