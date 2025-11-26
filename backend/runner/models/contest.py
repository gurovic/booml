from django.conf import settings
from django.db import models

from .course import Course, CourseParticipant


class Contest(models.Model):
    """
    Contest bound to one or more courses; visibility controlled by publication state.
    """

    courses = models.ManyToManyField(
        Course,
        related_name="contests",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    problems = models.ManyToManyField("Problem", blank=True)
    source = models.CharField(max_length=255, blank=True, default="")
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
        first_course = self.courses.first()
        suffix = f" ({first_course})" if first_course else ""
        return f"{self.title}{suffix}"

    def is_visible_to(self, user):
        """
        Teachers of linked courses see drafts; published contests visible to course participants.
        """
        if self.is_published:
            return self.courses.filter(participants__user=user).exists()
        return self.courses.filter(
            participants__user=user,
            participants__role=CourseParticipant.Role.TEACHER,
        ).exists()
