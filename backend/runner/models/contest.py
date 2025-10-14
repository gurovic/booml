from django.db import models
from django.db.models import CharField, IntegerField, DateField, BooleanField

class Contest(models.Model):
  tasks = models.ManyToManyField("Task", null=True)
  source = CharField()
  _type = IntegerField(db_column="type", null=True)
  difficulty = IntegerField(null=True)
  start_time = DateField()
  duration = IntegerField(null=True)
  status = CharField(choices=[
    "user",
    "дорешка"
  ])
  open = BooleanField()
  leaderBoard = models.ForeignKey("LeaderBoard", on_delete=models.CASCADE)