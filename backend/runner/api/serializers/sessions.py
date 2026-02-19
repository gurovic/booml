from typing import Optional

from rest_framework import serializers

from ...models.notebook import Notebook
from ...models.problem import Problem


class NotebookCreateSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_problem_id(self, value: int) -> int:
        if value is None:
            return value
        try:
            problem = Problem.objects.get(pk=value)
        except Problem.DoesNotExist as exc:
            raise serializers.ValidationError("Problem not found") from exc
        self._problem = problem
        return value

    @property
    def problem(self) -> Optional[Problem]:
        return getattr(self, "_problem", None)


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


class SessionFilesQuerySerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255, allow_blank=False)


class SessionFileDownloadSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255, allow_blank=False)
    path = serializers.CharField(max_length=1000, allow_blank=False)


class SessionFileUploadSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255, allow_blank=False)
    file = serializers.FileField()
    path = serializers.CharField(max_length=1000, allow_blank=True, required=False, allow_null=True)


class SessionFilePreviewSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255, allow_blank=False)
    path = serializers.CharField(max_length=1000, allow_blank=False)
    max_rows = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    max_cols = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    delimiter = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)


class SessionFileChartSerializer(serializers.Serializer):
    CHART_TYPE_CHOICES = ("line", "bar", "scatter", "hist", "box")
    AGGREGATION_CHOICES = ("mean", "sum", "median", "min", "max", "count")

    session_id = serializers.CharField(max_length=255, allow_blank=False)
    path = serializers.CharField(max_length=1000, allow_blank=False)
    chart_type = serializers.ChoiceField(
        choices=CHART_TYPE_CHOICES,
        required=False,
        allow_null=True,
    )
    x = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    y = serializers.JSONField(required=False, allow_null=True)
    agg = serializers.ChoiceField(
        choices=AGGREGATION_CHOICES,
        required=False,
        allow_null=True,
    )
    bins = serializers.IntegerField(min_value=2, max_value=200, required=False, allow_null=True)
    row_limit = serializers.IntegerField(min_value=1, max_value=50000, required=False, allow_null=True)
    max_points = serializers.IntegerField(min_value=10, max_value=5000, required=False, allow_null=True)
    top_n = serializers.IntegerField(min_value=1, max_value=200, required=False, allow_null=True)
    delimiter = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    render_image = serializers.BooleanField(required=False, default=True)
