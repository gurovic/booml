import uuid

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
    )
    # Order of contests inside a course (lower comes first).
    position = models.PositiveIntegerField(default=0, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    problems = models.ManyToManyField(
        "Problem",
        blank=True,
        through="ContestProblem",
        related_name="contests",
    )
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
    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        help_text="Moderation status of the contest",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_contests",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.course})"

    def is_visible_to(self, user):
        """
        Drafts are visible only to course teachers (including course owner).
        Published contests follow access_type and course membership.
        """
        if not user.is_authenticated:
            return False

        is_admin = user.is_staff or user.is_superuser
        is_teacher = (
            self.course.owner_id == user.id
            or self.course.participants.filter(user=user, role=CourseParticipant.Role.TEACHER).exists()
        )
        if is_admin or is_teacher:
            return True

        # Only approved & published contests are visible to non-owners.
        if not self.is_published or self.approval_status != self.ApprovalStatus.APPROVED:
            return False

        if self.access_type == self.AccessType.PRIVATE:
            return self.allowed_participants.filter(pk=user.pk).exists()

        if self.access_type == self.AccessType.LINK:
            if self.allowed_participants.filter(pk=user.pk).exists():
                return True

        if self.access_type == self.AccessType.PUBLIC and self.course.is_open:
            return True

        return self.course.participants.filter(user=user).exists()

    def ensure_access_token(self):
        if not self.access_token:
            self.access_token = uuid.uuid4().hex
            self.save(update_fields=["access_token"])
        return self.access_token


class ContestProblem(models.Model):
    """
    Through model for Contest <-> Problem relation with stable ordering.

    Note: db_table matches the auto-generated M2M table name to preserve existing data.
    """

    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    problem = models.ForeignKey("Problem", on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        db_table = "runner_contest_problems"
        ordering = ["position", "id"]
        unique_together = (("contest", "problem"),)
        indexes = [
            models.Index(fields=["contest", "position"], name="runner_contestprob_pos_idx"),
        ]
