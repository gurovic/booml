from __future__ import annotations

from django.conf import settings
from django.db import models

from .contest import Contest


class ContestNotification(models.Model):
    class Kind(models.TextChoices):
        ANNOUNCEMENT = "announcement", "Announcement"
        QUESTION = "question", "Question"
        ANSWER = "answer", "Answer"

    class Audience(models.TextChoices):
        ALL_PARTICIPANTS = "all_participants", "All participants"
        SELECTED_PARTICIPANTS = "selected_participants", "Selected participants"
        TEACHERS = "teachers", "Teachers"
        QUESTION_AUTHOR = "question_author", "Question author"

    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contest_notifications_authored",
    )
    kind = models.CharField(
        max_length=24,
        choices=Kind.choices,
    )
    audience = models.CharField(
        max_length=32,
        choices=Audience.choices,
    )
    text = models.TextField()
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["contest", "created_at"], name="runner_contestnotif_ct_idx"),
            models.Index(fields=["contest", "kind"], name="runner_contestnotif_kind_idx"),
            models.Index(fields=["parent", "created_at"], name="runner_contestnotif_parent_idx"),
        ]

    def __str__(self) -> str:
        return f"ContestNotification(id={self.id}, contest={self.contest_id}, kind={self.kind})"


class ContestNotificationRecipient(models.Model):
    notification = models.ForeignKey(
        ContestNotification,
        on_delete=models.CASCADE,
        related_name="recipient_links",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contest_notification_links",
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("notification", "user"),)
        indexes = [
            models.Index(fields=["user", "is_read"], name="runner_cntnotifrec_u_idx"),
            models.Index(fields=["notification", "user"], name="runner_cntnotifrec_n_idx"),
        ]

    def __str__(self) -> str:
        return (
            "ContestNotificationRecipient("
            f"notification={self.notification_id}, user={self.user_id}, is_read={self.is_read})"
        )
