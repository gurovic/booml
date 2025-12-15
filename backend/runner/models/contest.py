import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
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
    class Scoring(models.TextChoices):
        ICPC = "icpc", "ICPC (penalty by time)"
        IOI = "ioi", "IOI (sum of scores)"
        PARTIAL = "partial", "Partial scoring"

    scoring = models.CharField(
        max_length=20,
        choices=Scoring.choices,
        default=Scoring.IOI,
        help_text="How points are aggregated for the contest",
    )
    class Registration(models.TextChoices):
        OPEN = "open", "Open"
        APPROVAL = "approval", "By approval"
        INVITE = "invite", "By invitation"

    registration_type = models.CharField(
        max_length=20,
        choices=Registration.choices,
        default=Registration.OPEN,
        help_text="Who can register / how participants join the contest",
    )
    class AccessType(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        LINK = "link", "By link"

    access_type = models.CharField(
        max_length=20,
        choices=AccessType.choices,
        default=AccessType.PUBLIC,
        help_text="Controls who can see and join the contest",
    )
    access_token = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Token for link-based access",
    )
    allowed_participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="allowed_contests",
        help_text="Users explicitly allowed to access a private contest",
    )
    is_rated = models.BooleanField(
        default=False,
        help_text="If true, contest results affect participant rating",
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

    def clean(self):
        if self.course is None:
            raise ValidationError("Contest must belong to a course.")
        super().clean()

    def save(self, *args, **kwargs):
        # Guard against orphan contests even when bypassing forms/services.
        self.full_clean()
        return super().save(*args, **kwargs)

    def is_visible_to(self, user):
        """
        Teachers of linked courses always see the contest.
        Drafts are hidden from non-teachers.
        Visibility for others depends on access_type and explicit allows.
        """
        if not user.is_authenticated:
            return False

        is_teacher = self.course and self.course.participants.filter(
            user=user,
            role=CourseParticipant.Role.TEACHER,
        ).exists()
        if is_teacher:
            return True

        if not self.is_published:
            return False

        if self.access_type == self.AccessType.PRIVATE:
            return self.allowed_participants.filter(pk=user.pk).exists()

        if self.access_type == self.AccessType.LINK:
            if self.allowed_participants.filter(pk=user.pk).exists():
                return True

        if self.course:
            return self.course.participants.filter(user=user).exists()
        return False

    def ensure_access_token(self):
        if not self.access_token:
            self.access_token = uuid.uuid4().hex
            self.save(update_fields=["access_token"])
        return self.access_token
