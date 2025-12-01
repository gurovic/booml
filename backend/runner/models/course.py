from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.core.exceptions import ValidationError


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_open = models.BooleanField(
        default=False,
        help_text="Visible to any authenticated user when True",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        help_text=(
            "Optional parent course to build hierarchies (e.g., sections/years). "
            "Parent cannot be deleted while children exist."
        ),
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
        indexes = [models.Index(fields=["parent"], name="runner_course_parent_idx")]

    def __str__(self):
        return self.title

    def clean(self):
        """Prevent cycles in course hierarchy."""
        if self.parent:
            if self.parent_id == self.id:
                raise ValidationError("Course cannot be its own parent")

            visited = set()
            current = self.parent
            while current:
                if current.pk:
                    if current.pk in visited:
                        raise ValidationError("Circular course hierarchy detected")
                    visited.add(current.pk)
                    if self.pk and current.pk == self.pk:
                        raise ValidationError("Course cannot reference itself in hierarchy")
                current = current.parent
        super().clean()


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
