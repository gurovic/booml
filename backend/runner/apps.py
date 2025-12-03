from django.apps import AppConfig


class RunnerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'runner'
    verbose_name = 'Тестирующая система'
    def ready(self):
        from runner.services.runtime import register_runtime_shutdown_hooks
        register_runtime_shutdown_hooks()
