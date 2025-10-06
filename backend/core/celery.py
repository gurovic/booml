import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "booml.settings")

app = Celery("booml")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
