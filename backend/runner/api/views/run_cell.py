from urllib.parse import urlencode

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.urls import reverse

from ...services.runtime import SessionNotFoundError, run_code, provide_input
from ..serializers import CellRunInputSerializer, CellRunSerializer
from .sessions import ensure_notebook_access


class RunCellView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CellRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cell = serializer.cell
        assert cell is not None

        ensure_notebook_access(request.user, cell.notebook)

        session_id = serializer.validated_data["session_id"]
        try:
            result = run_code(session_id, cell.content or "")
        except SessionNotFoundError:
            return Response(
                {"detail": "Сессия не создана. Сначала создайте новую сессию."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outputs = _attach_output_urls(request, session_id, result.outputs or [])
        artifacts = _build_artifacts(outputs, result.artifacts or [])

        status_value = result.status or ("error" if result.error else "success")

        return Response(
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "status": status_value,
                "prompt": result.prompt or "",
                "run_id": result.run_id,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.error,
                "variables": result.variables,
                "outputs": outputs,
                "artifacts": artifacts,
            },
            status=status.HTTP_200_OK,
        )


class RunCellInputView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CellRunInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cell = serializer.cell
        assert cell is not None

        ensure_notebook_access(request.user, cell.notebook)

        session_id = serializer.validated_data["session_id"]
        run_id = serializer.validated_data["run_id"]
        text = serializer.validated_data.get("input")
        stdin_eof = bool(serializer.validated_data.get("stdin_eof"))

        try:
            result = provide_input(session_id, run_id, text, stdin_eof=stdin_eof)
        except SessionNotFoundError:
            return Response(
                {"detail": "Сессия не создана. Сначала создайте новую сессию."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outputs = _attach_output_urls(request, session_id, result.outputs or [])
        artifacts = _build_artifacts(outputs, result.artifacts or [])
        status_value = result.status or ("error" if result.error else "success")

        return Response(
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "status": status_value,
                "prompt": result.prompt or "",
                "run_id": result.run_id,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.error,
                "variables": result.variables,
                "outputs": outputs,
                "artifacts": artifacts,
            },
            status=status.HTTP_200_OK,
        )


def _attach_output_urls(request, session_id: str, outputs: list[dict]) -> list[dict]:
    if not outputs:
        return []
    url_template = reverse("session-file-download")
    hydrated: list[dict] = []
    for item in outputs:
        if not isinstance(item, dict):
            continue
        next_item = dict(item)
        path = next_item.get("path")
        if path:
            query = urlencode({"session_id": session_id, "path": path})
            next_item["url"] = request.build_absolute_uri(f"{url_template}?{query}")
        hydrated.append(next_item)
    return hydrated


def _build_artifacts(outputs: list[dict], artifacts: list[dict]) -> list[dict]:
    combined = []
    seen = set()
    for item in artifacts or []:
        path = item.get("path")
        if not path or path in seen:
            continue
        seen.add(path)
        combined.append(item)
    for item in outputs or []:
        path = item.get("path")
        if not path or path in seen:
            continue
        seen.add(path)
        name = item.get("name") or path
        combined.append({"name": name, "path": path})
    return combined
