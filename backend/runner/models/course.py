from django.conf import settings
from django.db import models


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_open = models.BooleanField(
        default=False,
        help_text="Visible to any authenticated user when True",
    )
    section = models.ForeignKey(
        "Section",
        on_delete=models.PROTECT,
        related_name="courses",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_courses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["section"], name="runner_course_section_idx")]

    def __str__(self):
        return self.title



class CourseParticipant(models.Model):
    class Role(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_participations",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    is_owner = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "user")
        indexes = [
            models.Index(fields=["course", "role"], name="runner_course_role_idx"),
            models.Index(fields=["user", "role"], name="runner_user_role_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["course"],
                condition=models.Q(is_owner=True),
                name="unique_course_owner",
            )
        ]

    def __str__(self):
        return f"{self.user} in {self.course} as {self.role}"


class FavoriteCourse(models.Model):
    """
    Per-user favorite courses, displayed on HomePage in a stable order.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_courses",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    # Lower comes first.
    position = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]
        unique_together = ("user", "course")
        indexes = [
            models.Index(fields=["user", "position"], name="runner_favcourse_userpos_idx"),
            models.Index(fields=["course", "user"], name="runner_fav_crsusr_idx"),
        ]

    def __str__(self):
        return f"{self.user} -> {self.course}"
