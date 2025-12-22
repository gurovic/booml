from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

from .course import Course


class Section(models.Model):
    """
    A hierarchical container that groups either child sections OR courses.
    A section cannot contain both sections and courses simultaneously.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent section. Root sections have no parent.",
    )
    courses = models.ManyToManyField(
        Course,
        blank=True,
        related_name="sections",
        help_text="Courses in this section. Mutually exclusive with child sections.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_sections",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the parent section.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        indexes = [
            models.Index(fields=["parent"], name="runner_section_parent_idx"),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        """
        Validates that:
        1. No circular hierarchy exists
        2. Section does not contain both child sections and courses
        """
        # Check for circular hierarchy
        if self.parent:
            if self.parent_id == self.id:
                raise ValidationError("Section cannot be its own parent.")

            visited = set()
            current = self.parent
            while current:
                if current.pk:
                    if current.pk in visited:
                        raise ValidationError("Circular section hierarchy detected.")
                    visited.add(current.pk)
                    if self.pk and current.pk == self.pk:
                        raise ValidationError(
                            "Section cannot reference itself in hierarchy."
                        )
                current = current.parent

        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def has_child_sections(self) -> bool:
        """Returns True if this section has any child sections."""
        return self.children.exists()

    def has_courses(self) -> bool:
        """Returns True if this section has any courses."""
        return self.courses.exists()

    def can_add_course(self) -> bool:
        """Returns True if a course can be added to this section."""
        return not self.has_child_sections()

    def can_add_child_section(self) -> bool:
        """Returns True if a child section can be added to this section."""
        return not self.has_courses()

    def add_course(self, course: Course):
        """
        Adds a course to this section.
        Raises ValidationError if section already contains child sections.
        """
        if self.has_child_sections():
            raise ValidationError(
                "Cannot add course to a section that contains child sections."
            )
        self.courses.add(course)

    def add_child_section(self, section: "Section"):
        """
        Adds a child section to this section.
        Raises ValidationError if section already contains courses.
        """
        if self.has_courses():
            raise ValidationError(
                "Cannot add child section to a section that contains courses."
            )
        section.parent = self
        section.save()
