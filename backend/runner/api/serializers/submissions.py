from rest_framework import serializers
from django.contrib.auth import get_user_model

from ...models.submission import Submission
from ...models.task import Task

User = get_user_model()


class SubmissionCreateSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(write_only=True)
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Submission
        fields = ["id", "task_id", "file", "submitted_at", "status", "code_size"]
        read_only_fields = ["id", "submitted_at", "status", "code_size"]

    def validate_file(self, f):
        max_mb = 50
        if f.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"Файл слишком большой (> {max_mb}MB)")
        name = (getattr(f, "name", "") or "").lower()
        if not name.endswith(".csv"):
            raise serializers.ValidationError("Ожидается CSV файл (.csv)")
        return f

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        task_id = validated_data.pop("task_id")

        try:
            task = Task.objects.get(pk=task_id)
        except Task.DoesNotExist:
            raise serializers.ValidationError({"task_id": "Задача (Task) не найдена"})

        submission = Submission.objects.create(user=user, task=task, **validated_data)
        return submission


class SubmissionReadSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(source="task.id", read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)
    file_url = serializers.FileField(source="file", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id", "task_id", "task_title", "file_url",
            "submitted_at", "status", "code_size", "metrics",
        ]

