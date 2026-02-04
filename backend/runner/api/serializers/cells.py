from typing import Optional

from rest_framework import serializers

from ...models.cell import Cell


class CellRunSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255, allow_blank=False)
    cell_id = serializers.IntegerField(min_value=1)
    stdin = serializers.CharField(required=False, allow_null=True)
    run_id = serializers.CharField(required=False, allow_null=True)
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
