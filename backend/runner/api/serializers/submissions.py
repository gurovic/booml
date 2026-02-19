from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils.crypto import get_random_string

from ...models.submission import Submission
from ...models.problem import Problem
from ...models.prevalidation import PreValidation

User = get_user_model()


class SubmissionCreateSerializer(serializers.ModelSerializer):
    problem_id = serializers.IntegerField(write_only=True)
    file = serializers.FileField(write_only=True, required=False, allow_null=True)
    raw_text = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
    )

    MAX_FILE_MB = 50

    class Meta:
        model = Submission
        fields = ["id", "problem_id", "file", "raw_text", "submitted_at", "status", "code_size"]
        read_only_fields = ["id", "submitted_at", "status", "code_size"]

    def validate_file(self, f):
        max_mb = self.MAX_FILE_MB
        if f.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"Файл слишком большой (> {max_mb}MB)")
        name = (getattr(f, "name", "") or "").lower()
        if not name.endswith(".csv"):
            raise serializers.ValidationError("Ожидается CSV файл (.csv)")
        return f

    def validate_raw_text(self, value):
        if value is None:
            return value

        text = value.strip()
        if not text:
            raise serializers.ValidationError("Текстовое решение не должно быть пустым")

        max_bytes = self.MAX_FILE_MB * 1024 * 1024
        size_bytes = len(value.encode("utf-8"))
        if size_bytes > max_bytes:
            raise serializers.ValidationError(f"Текст слишком большой (> {self.MAX_FILE_MB}MB)")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        has_file = attrs.get("file") is not None
        has_text = bool(attrs.get("raw_text"))

        if has_file == has_text:
            raise serializers.ValidationError(
                {"non_field_errors": ["Передайте либо CSV-файл, либо текст решения"]}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        problem_id = validated_data.pop("problem_id")
        raw_text = validated_data.get("raw_text")

        try:
            problem = Problem.objects.get(pk=problem_id)
        except Problem.DoesNotExist:
            raise serializers.ValidationError({"problem_id": "Задача (Problem) не найдена"})

        if raw_text:
            filename = f"submission_{get_random_string(10)}.csv"
            validated_data["file"] = ContentFile(raw_text.encode("utf-8"), name=filename)
            validated_data["source"] = Submission.SOURCE_TEXT
        else:
            validated_data["source"] = Submission.SOURCE_FILE

        submission = Submission.objects.create(user=user, problem=problem, **validated_data)
        return submission


class SubmissionReadSerializer(serializers.ModelSerializer):
    problem_id = serializers.IntegerField(source="problem.id", read_only=True)
    problem_title = serializers.CharField(source="problem.title", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id", "problem_id", "problem_title", "file_url",
            "submitted_at", "status", "code_size", "metrics",
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            # Return relative URL path (e.g., /media/submissions/file.csv)
            # Browser will resolve it relative to current origin
            return obj.file.url
        return None


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
    file_url = serializers.SerializerMethodField()
    prevalidation = PreValidationSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id", "problem_id", "problem_title", "file_url",
            "submitted_at", "status", "code_size", "metrics",
            "prevalidation",
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            # Return relative URL path (e.g., /media/submissions/file.csv)
            # Browser will resolve it relative to current origin
            return obj.file.url
        return None
