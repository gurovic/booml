from django.conf import settings
from django.db import models

from .course import Course, CourseParticipant


class Contest(models.Model):
    """
    Contest is bound to a single course; visibility controlled by publication state and status.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="contests",
        null=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    problems = models.ManyToManyField("Problem", blank=True)
    source = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional source label or namespace for the contest",
    )
    start_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Contest duration in minutes",
    )
    is_published = models.BooleanField(
        default=False,
        help_text=(
            "When True the contest is visible to all course participants; "
            "otherwise only course teachers can see it."
        ),
    )
    class Status(models.IntegerChoices):
        GOING = 0, "going"
        AFTER_SOLVING = 1, "after-solving"

    status = models.IntegerField(choices=Status.choices, default=Status.GOING)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_contests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.course})"

    def is_visible_to(self, user):
        """
        Teachers of linked courses see drafts; published contests visible to course participants.
        """
        if self.is_published:
            return self.course.participants.filter(user=user).exists()
        return self.course.participants.filter(
            user=user,
            role=CourseParticipant.Role.TEACHER,
        ).exists()
