from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from ...models.notebook import Notebook
from ...services.runtime import SessionNotFoundError
from ...services.streaming_runs import (
    get_streaming_run,
    read_stream_output,
    start_streaming_run,
)
from ..serializers import CellRunSerializer, CellRunStreamStatusSerializer
from .run_cell import _attach_output_urls, _build_artifacts
from .sessions import ensure_notebook_access


class RunCellStreamStartView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CellRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cell = serializer.cell
        assert cell is not None

        ensure_notebook_access(request.user, cell.notebook)
        session_id = serializer.validated_data["session_id"]

        try:
            run = start_streaming_run(
                session_id=session_id,
                cell_id=cell.id,
                notebook_id=cell.notebook_id,
                code=cell.content or "",
            )
        except SessionNotFoundError:
            return Response(
                {"detail": "Сессия не создана. Сначала создайте новую сессию."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "run_id": run.run_id,
                "status": run.status,
                "session_id": session_id,
                "cell_id": cell.id,
            },
            status=status.HTTP_200_OK,
        )


class RunCellStreamStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = CellRunStreamStatusSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        run_id = serializer.validated_data["run_id"]
        stdout_offset = serializer.validated_data.get("stdout_offset") or 0
        stderr_offset = serializer.validated_data.get("stderr_offset") or 0

        run = get_streaming_run(run_id)
        if run is None:
            return Response({"detail": "Run not found"}, status=status.HTTP_404_NOT_FOUND)

        notebook = get_object_or_404(Notebook, pk=run.notebook_id)
        ensure_notebook_access(request.user, notebook)

        stdout_chunk, stderr_chunk, stdout_next, stderr_next = read_stream_output(
            run,
            stdout_offset=stdout_offset,
            stderr_offset=stderr_offset,
        )

        payload = {
            "run_id": run_id,
            "status": run.status,
            "stdout": stdout_chunk,
            "stderr": stderr_chunk,
            "stdout_offset": stdout_next,
            "stderr_offset": stderr_next,
        }

        if run.status == "error":
            payload["detail"] = run.error or "Ошибка выполнения"

        if run.status == "finished" and run.result is not None:
            outputs = _attach_output_urls(request, run.session_id, run.result.outputs or [])
            artifacts = _build_artifacts(outputs, run.result.artifacts or [])
            payload["result"] = {
                "session_id": run.session_id,
                "cell_id": run.cell_id,
                "stdout": run.result.stdout,
                "stderr": run.result.stderr,
                "error": run.result.error,
                "variables": run.result.variables,
                "outputs": outputs,
                "artifacts": artifacts,
            }

        return Response(payload, status=status.HTTP_200_OK)
