from django.apps import AppConfig


class RunnerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'runner'
    verbose_name = 'Тестирующая система'
