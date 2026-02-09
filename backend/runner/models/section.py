from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Section(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        help_text="Optional parent section to build nested structure.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_sections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [models.Index(fields=["parent"], name="runner_section_parent_idx")]

    def __str__(self):
        return self.title

    def clean(self):
        """Prevent cycles in section hierarchy."""
        if self.parent:
            if self.parent_id == self.id:
                raise ValidationError("Section cannot be its own parent")

            visited = set()
            current = self.parent
            while current:
                if current.pk:
                    if current.pk in visited:
                        raise ValidationError("Circular section hierarchy detected")
                    visited.add(current.pk)
                    if self.pk and current.pk == self.pk:
                        raise ValidationError("Section cannot reference itself in hierarchy")
                current = current.parent
        super().clean()


class SectionTeacher(models.Model):
    """
    Extra teachers (besides the owner) who can manage a section:
    - create courses inside the section
    - create nested sections under it

    Root categories do not need explicit memberships: any teacher can create inside them.
    """

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="section_teachers",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="section_teacher_memberships",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("section", "user")
        indexes = [
            models.Index(fields=["section", "user"], name="runner_secteacher_secusr_idx"),
            models.Index(fields=["user", "section"], name="runner_secteacher_usrsec_idx"),
        ]

    def __str__(self):
        return f"{self.user} teacher in {self.section}"
