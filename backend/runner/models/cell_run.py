from django.db import models
from django.contrib.auth import get_user_model

from .cell import Cell
from .notebook import Notebook

User = get_user_model()


class CellRun(models.Model):
    STATUS_RUNNING = "running"
    STATUS_FINISHED = "finished"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "Выполняется"),
        (STATUS_FINISHED, "Завершено"),
        (STATUS_ERROR, "Ошибка"),
    ]

    cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name="runs")
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, related_name="cell_runs")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cell_runs",
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    run_id = models.CharField(max_length=64, blank=True, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Запуск ячейки"
        verbose_name_plural = "Очередь выполнения ячеек"

    def __str__(self) -> str:
        return f"CellRun #{self.pk} cell={self.cell_id} status={self.status}"

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
