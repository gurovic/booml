from rest_framework import serializers
from django.contrib.auth import get_user_model

from ...models.submission import Submission
from ...models.problem import Problem
from ...models.prevalidation import PreValidation
from ...services.problem_scoring import (
    default_curve_p,
    extract_raw_metric,
    extract_score_100,
    resolve_score_spec,
    score_from_raw,
)

User = get_user_model()


def _extract_submission_score(submission: Submission):
    metrics = getattr(submission, "metrics", None)
    score_100 = extract_score_100(metrics)
    if score_100 is not None:
        return score_100

    problem = getattr(submission, "problem", None)
    descriptor = getattr(problem, "descriptor", None) if problem is not None else None

    metric_name = "metric"
    if isinstance(metrics, dict):
        raw_metric_name = metrics.get("raw_metric_name")
        if isinstance(raw_metric_name, str) and raw_metric_name.strip():
            metric_name = raw_metric_name.strip()
    if descriptor is not None:
        descriptor_metric = (getattr(descriptor, "metric", "") or "").strip()
        descriptor_metric_name = (getattr(descriptor, "metric_name", "") or "").strip()
        metric_name = descriptor_metric or descriptor_metric_name or metric_name

    raw_metric = extract_raw_metric(metrics, metric_name=metric_name)
    if raw_metric is None:
        return None

    score_spec = resolve_score_spec(
        metric_name,
        descriptor_direction=getattr(descriptor, "score_direction", "") if descriptor else "",
        descriptor_ideal=getattr(descriptor, "score_ideal_metric", None) if descriptor else None,
    )

    reference_metric = getattr(descriptor, "score_reference_metric", None) if descriptor else None
    curve_p = getattr(descriptor, "score_curve_p", None) if descriptor else None
    nonlinear_reference = (
        float(reference_metric)
        if isinstance(reference_metric, (int, float))
        and abs(float(reference_metric) - float(score_spec.ideal)) > 1e-12
        else None
    )
    nonlinear_curve = (
        float(curve_p)
        if isinstance(curve_p, (int, float))
        else default_curve_p(score_spec.direction)
    )
    score_100, _ = score_from_raw(
        float(raw_metric),
        metric_name=metric_name,
        direction=score_spec.direction,
        ideal=float(score_spec.ideal),
        reference=nonlinear_reference,
        curve_p=nonlinear_curve,
    )
    return float(score_100)


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
    file_url = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id", "problem_id", "problem_title", "file_url",
            "submitted_at", "status", "code_size", "metrics", "score",
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            # Return relative URL path (e.g., /media/submissions/file.csv)
            # Browser will resolve it relative to current origin
            return obj.file.url
        return None

    def get_score(self, obj):
        return _extract_submission_score(obj)


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
    score = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id", "problem_id", "problem_title", "file_url",
            "submitted_at", "status", "code_size", "metrics", "score",
            "prevalidation",
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            # Return relative URL path (e.g., /media/submissions/file.csv)
            # Browser will resolve it relative to current origin
            return obj.file.url
        return None

    def get_score(self, obj):
        return _extract_submission_score(obj)

