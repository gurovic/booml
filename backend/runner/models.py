from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .tasks import enqueue_submission_for_evaluation


class Submission(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_ACCEPTED = "accepted"
    STATUS_FAILED = "failed"
    STATUS_VALIDATED = "validated"
    STATUS_CHOICES = [
        ("pending", "⏳ В очереди"),
        ("running", "🏃 Выполняется"),
        ("accepted", "✅ Принято"),
        ("failed", "❌ Ошибка"),
        ("validated", "✅ Валидировано")
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    problem = models.ForeignKey("Problem", on_delete=models.CASCADE, related_name="submissions")
    file = models.FileField(upload_to="submissions/")
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    code_size = models.PositiveIntegerField(default=0)
    metrics = models.JSONField(null=True, blank=True)  # {"accuracy": 0.87, "f1": 0.65}

    def save(self, *args, **kwargs):
        if self.file and not self.code_size:
            try:
                self.code_size = self.file.size
            except Exception:
                self.code_size = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.problem} ({self.score})"


@receiver(pre_save, sender=Submission)
def submission_pre_save(sender, instance, **kwargs):
    """
    Сохраняем предыдущий статус в временное поле instance._previous_status.
    Это нужно, чтобы в post_save понять, изменился ли статус.
    """
    if not instance.pk:
        instance._previous_status = None
    else:
        try:
            prev = Submission.objects.get(pk=instance.pk)
            instance._previous_status = prev.status
        except Submission.DoesNotExist:
            instance._previous_status = None


@receiver(post_save, sender=Submission)
def submission_post_save(sender, instance, created, **kwargs):
    """
    Если статус только что стал 'validated' (и раньше не был 'validated'),
    автоматически переводим объект в 'pending' (в очередь) и ставим задачу в Celery.
    Используем QuerySet.update(...) чтобы не вызывать повторно save()/сигналы.
    """
    prev_status = getattr(instance, "_previous_status", None)

    # реагируем только при переходе в 'validated' (и не при создании)
    if not created and instance.status == Submission.STATUS_VALIDATED and prev_status != Submission.STATUS_VALIDATED:
        # читаем текущее значение в БД (на случай гонок)
        current_db_status = Submission.objects.filter(pk=instance.pk).values_list("status", flat=True).first()

        # если в БД уже в очереди/выполняется/принято — пропускаем
        if current_db_status in (Submission.STATUS_PENDING, Submission.STATUS_RUNNING, Submission.STATUS_ACCEPTED):
            return

        # атомарно обновляем статус в БД (без вызова .save и без сигналов)
        updated_count = Submission.objects.filter(pk=instance.pk, status=instance.status).update(
            status=Submission.STATUS_PENDING)

        # если обновление прошло (== 1), ставим таск в очередь
        if updated_count:
            enqueue_submission_for_evaluation.delay(instance.pk)


from django.db import models

# Create your models here.
