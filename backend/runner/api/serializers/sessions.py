from typing import Optional

from rest_framework import serializers

from ...models.notebook import Notebook


class NotebookSessionCreateSerializer(serializers.Serializer):
    notebook_id = serializers.IntegerField(min_value=1)

    def validate_notebook_id(self, value: int) -> int:
        try:
            notebook = Notebook.objects.get(pk=value)
        except Notebook.DoesNotExist as exc:
            raise serializers.ValidationError("Notebook not found") from exc
        self._notebook = notebook
        return value

    @property
    def notebook(self) -> Optional[Notebook]:
        return getattr(self, "_notebook", None)


class SessionResetSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255, allow_blank=False)
