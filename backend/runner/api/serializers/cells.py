from typing import Optional

from rest_framework import serializers

from ...models.cell import Cell


class CellRunSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255, allow_blank=False)
    cell_id = serializers.IntegerField(min_value=1)

    def validate_cell_id(self, value: int) -> int:
        try:
            cell = Cell.objects.select_related("notebook").get(pk=value)
        except Cell.DoesNotExist as exc:
            raise serializers.ValidationError("Cell not found") from exc

        if cell.cell_type != Cell.CODE:
            raise serializers.ValidationError("Cell is not executable")

        self._cell = cell
        return value

    @property
    def cell(self) -> Optional[Cell]:
        return getattr(self, "_cell", None)


class CellRunStreamStatusSerializer(serializers.Serializer):
    run_id = serializers.CharField(max_length=64, allow_blank=False)
    stdout_offset = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    stderr_offset = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class CellRunInputSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255, allow_blank=False)
    cell_id = serializers.IntegerField(min_value=1)
    run_id = serializers.CharField(max_length=64, allow_blank=False)
    input = serializers.CharField(allow_blank=True, required=False, allow_null=True)
    stdin_eof = serializers.BooleanField(required=False, default=False)

    def validate_cell_id(self, value: int) -> int:
        try:
            cell = Cell.objects.select_related("notebook").get(pk=value)
        except Cell.DoesNotExist as exc:
            raise serializers.ValidationError("Cell not found") from exc

        if cell.cell_type != Cell.CODE:
            raise serializers.ValidationError("Cell is not executable")

        self._cell = cell
        return value

    @property
    def cell(self) -> Optional[Cell]:
        return getattr(self, "_cell", None)
