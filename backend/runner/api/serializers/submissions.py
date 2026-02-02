from rest_framework import serializers
from django.contrib.auth import get_user_model

from ...models.submission import Submission
from ...models.problem import Problem
from ...models.prevalidation import PreValidation

User = get_user_model()


class SubmissionCreateSerializer(serializers.ModelSerializer):
    problem_id = serializers.IntegerField(write_only=True)
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Submission
        fields = ["id", "problem_id", "file", "submitted_at", "status", "code_size"]
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
        problem_id = validated_data.pop("problem_id")

        try:
            problem = Problem.objects.get(pk=problem_id)
        except Problem.DoesNotExist:
            raise serializers.ValidationError({"problem_id": "Задача (Problem) не найдена"})

        submission = Submission.objects.create(user=user, problem=problem, **validated_data)
        return submission


class SubmissionReadSerializer(serializers.ModelSerializer):
    problem_id = serializers.IntegerField(source="problem.id", read_only=True)
    problem_title = serializers.CharField(source="problem.title", read_only=True)
    file_url = serializers.FileField(source="file", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id", "problem_id", "problem_title", "file_url",
            "submitted_at", "status", "code_size", "metrics",
        ]


class PreValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreValidation
        fields = [
            "id", "valid", "status", "errors_count", "warnings_count",
            "rows_total", "unique_ids", "first_id", "last_id",
            "duration_ms", "errors", "warnings", "stats", "created_at",
        ]


class SubmissionDetailSerializer(serializers.ModelSerializer):
    problem_id = serializers.IntegerField(source="problem.id", read_only=True)
    problem_title = serializers.CharField(source="problem.title", read_only=True)
    file_url = serializers.FileField(source="file", read_only=True)
    prevalidation = PreValidationSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id", "problem_id", "problem_title", "file_url",
            "submitted_at", "status", "code_size", "metrics",
            "prevalidation",
        ]

