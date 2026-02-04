from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ...services.runtime import SessionNotFoundError, run_code
from ..serializers import CellRunSerializer
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
        stdin = serializer.validated_data.get("stdin")
        run_id = serializer.validated_data.get("run_id")
        stdin_eof = serializer.validated_data.get("stdin_eof", False)
        try:
            result = run_code(
                session_id,
                cell.content or "",
                stdin=stdin,
                run_id=run_id,
                stdin_eof=stdin_eof,
            )
        except SessionNotFoundError:
            return Response(
                {"detail": "Сессия не создана. Сначала создайте новую сессию."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "session_id": session_id,
                "cell_id": cell.id,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.error,
                "variables": result.variables,
                "status": getattr(result, "status", "success"),
                "prompt": getattr(result, "prompt", None),
                "run_id": getattr(result, "run_id", None),
            },
            status=status.HTTP_200_OK,
        )
