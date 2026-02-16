from django.db import models


class SiteUpdate(models.Model):
    """
    Simple "what's new" entries shown on the HomePage sidebar.

    Editable via Django admin.
    """

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

