from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Section(models.Model):
    ROOT_TITLES = ("Авторское", "Тематическое", "Олимпиады")

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_public = models.BooleanField(default=False)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        help_text="Sections can be nested; parent cannot be deleted while children exist.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_sections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["parent"], name="runner_section_parent_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["title"],
                condition=Q(parent__isnull=True),
                name="runner_unique_root_section_title",
            )
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        if not self.parent:
            if self.title not in self.ROOT_TITLES:
                raise ValidationError(
                    "Только три корневых раздела разрешены: Авторское, Тематическое, Олимпиады."
                )
            super().clean()
            return

        if self.parent_id == self.id:
            raise ValidationError("Section cannot be its own parent.")
        if self.parent.owner_id != self.owner_id:
            raise ValidationError(
                "Владелец дочернего раздела должен совпадать с владельцем родительского раздела."
            )

        visited = set()
        ancestor = self.parent
        while ancestor:
            if ancestor.pk in visited:
                raise ValidationError("Circular section hierarchy detected.")
            visited.add(ancestor.pk)
            if self.pk and ancestor.pk == self.pk:
                raise ValidationError("Circular section hierarchy detected.")
            ancestor = ancestor.parent

        super().clean()

    def save(self, *args, **kwargs):
        # Ensure hierarchy/ownership rules are enforced even on direct model usage.
        self.full_clean()
        return super().save(*args, **kwargs)
