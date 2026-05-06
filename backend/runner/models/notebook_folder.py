from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class NotebookFolder(models.Model):
    SYSTEM_TASK_FOLDER_TITLE = "Блокноты для задач"

    class Kind(models.TextChoices):
        CUSTOM = "custom", "Custom"
        TASKS = "tasks", "Tasks"

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notebook_folders",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    kind = models.CharField(
        max_length=12,
        choices=Kind.choices,
        default=Kind.CUSTOM,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "kind"], name="notebook_folder_owner_kind_idx"),
            models.Index(fields=["owner", "parent"], name="nb_folder_owner_parent_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "kind"],
                condition=models.Q(kind="tasks"),
                name="unique_owner_tasks_notebook_folder",
            ),
        ]

    @property
    def is_system(self) -> bool:
        return self.kind == self.Kind.TASKS

    @classmethod
    def get_or_create_tasks_folder(cls, owner):
        folder, created = cls.objects.get_or_create(
            owner=owner,
            kind=cls.Kind.TASKS,
            defaults={"title": cls.SYSTEM_TASK_FOLDER_TITLE},
        )
        if not created and folder.title != cls.SYSTEM_TASK_FOLDER_TITLE:
            folder.title = cls.SYSTEM_TASK_FOLDER_TITLE
            folder.save(update_fields=["title", "updated_at"])
        return folder

    def __str__(self):
        return self.title
